import os
import sqlite3
import secrets
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 0))
SITE_URL = os.environ.get("SITE_URL", "https://alfakreditby.ru")

def init_db():
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fullname TEXT, phone TEXT, inn TEXT,
                  income REAL, term INTEGER, amount REAL, payment REAL,
                  session_id TEXT, status TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def send_to_admin(text, keyboard=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": ADMIN_CHAT_ID, "text": text, "parse_mode": "HTML"}
    if keyboard:
        data["reply_markup"] = keyboard
    try:
        requests.post(url, json=data)
    except Exception as e:
        print(f"Ошибка: {e}")

def send_callback_answer(callback_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_id, "text": text})

def get_keyboard(session_id):
    return {
        "inline_keyboard": [
            [{"text": "✅ ОДОБРИТЬ КРЕДИТ", "callback_data": f"approve_credit:{session_id}"}],
            [{"text": "❌ ОТКЛОНИТЬ", "callback_data": f"reject:{session_id}"}]
        ]
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'callback_query' in data:
        callback = data['callback_query']
        callback_id = callback['id']
        callback_data = callback['data']
        
        if callback_data.startswith('approve_credit:'):
            session_id = callback_data.split(':')[1]
            
            # ОБНОВЛЯЕМ СТАТУС
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE applications SET status = "approved" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            
            send_callback_answer(callback_id, "✅ Кредит одобрен!")
            send_to_admin(f"✅ Кредит ОДОБРЕН для сессии: {session_id}")
            
        elif callback_data.startswith('reject:'):
            session_id = callback_data.split(':')[1]
            
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE applications SET status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            
            send_callback_answer(callback_id, "❌ Заявка отклонена")
            send_to_admin(f"❌ Заявка ОТКЛОНЕНА. Сессия: {session_id}")
    
    return jsonify({"status": "ok"})

@app.route('/submit_credit_application', methods=['POST'])
def submit_application():
    data = request.json
    session_id = secrets.token_hex(8)
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''INSERT INTO applications (fullname, phone, inn, income, term, amount, payment, session_id, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (data['fullname'], data['phone'], data.get('inn', ''), data.get('income', 0),
               data['term'], data['amount'], data['payment'], session_id, 'pending'))
    conn.commit()
    conn.close()
    
    msg = f"""🆕 <b>НОВАЯ ЗАЯВКА</b>

👤 {data['fullname']}
📱 {data['phone']}
🆔 ИНН: {data.get('inn', '—')}
💰 {data['amount']} BYN
📅 {data['term']} мес.
💳 Платёж: ~{data['payment']} BYN

🆔 Сессия: <code>{session_id}</code>"""
    
    send_to_admin(msg, get_keyboard(session_id))
    return jsonify({"status": "ok", "session_id": session_id})

@app.route('/get_application/<session_id>', methods=['GET'])
def get_application(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT fullname, phone, amount, term, payment FROM applications WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({
            "fullname": row[0],
            "phone": row[1],
            "amount": row[2],
            "term": row[3],
            "payment": row[4]
        })
    return jsonify({"error": "not found"}), 404

@app.route('/check_status/<session_id>', methods=['GET'])
def check_status(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT status FROM applications WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0]})
    return jsonify({"status": "not_found"}), 404

@app.route('/')
def home():
    return "✅ API работает"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
