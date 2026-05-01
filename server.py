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
DB_PATH = "applications.db"

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
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def db_exec(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def db_one(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    row = c.fetchone()
    conn.close()
    return row

def tg(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print("Telegram error:", e)

def send_admin(text, keyboard=None):
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    tg("sendMessage", payload)

def answer_callback(callback_id, text):
    tg("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text,
        "show_alert": False
    })

def keyboard(session_id):
    return {
        "inline_keyboard": [
            [{"text": "✅ Одобрить", "callback_data": f"approve:{session_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"reject:{session_id}"}]
        ]
    }

@app.route("/")
def home():
    return "✅ API работает"

@app.route("/submit_credit_application", methods=["POST"])
def submit_credit_application():
    data = request.get_json(force=True)

    session_id = secrets.token_hex(12)

    fullname = data.get("fullname", "")
    phone = data.get("phone", "")
    inn = data.get("inn", "")
    term = int(data.get("term", 0))
    amount = float(data.get("amount", 0))
    payment = float(data.get("payment", 0))
    credit_history = data.get("credit_history", "")

    db_exec("""
        INSERT INTO applications
        (fullname, phone, inn, income, term, amount, payment, session_id, credit_history, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        fullname, phone, inn, 0, term, amount, payment,
        session_id, credit_history, "pending"
    ))

    text = f"""🆕 <b>НОВАЯ ЗАЯВКА</b>

👤 <b>ФИО:</b> {fullname}
📱 <b>Телефон:</b> {phone}
🆔 <b>ИНН:</b> {inn}
💰 <b>Сумма:</b> {amount:.0f} BYN
📅 <b>Срок:</b> {term} мес.
💳 <b>Платёж:</b> ~{payment:.0f} BYN
📊 <b>КИ:</b> {credit_history}

🆔 <b>Сессия:</b> <code>{session_id}</code>"""

    send_admin(text, keyboard(session_id))

    return jsonify({
        "status": "ok",
        "session_id": session_id
    })

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
    data = request.get_json(force=True)
    print("WEBHOOK:", data)

    callback = data.get("callback_query")
    if not callback:
        return jsonify({"ok": True})

    callback_id = callback.get("id")
    callback_data = callback.get("data", "")

    if ":" not in callback_data:
        answer_callback(callback_id, "Ошибка кнопки")
        return jsonify({"ok": True})

    action, session_id = callback_data.split(":", 1)

    # поддержка старых и новых кнопок
    if action in ["approve", "approve_credit"]:
        db_exec("UPDATE applications SET status = ? WHERE session_id = ?", ("approved", session_id))
        answer_callback(callback_id, "✅ Заявка одобрена")
        send_admin(f"✅ <b>Заявка ОДОБРЕНА</b>\nСессия: <code>{session_id}</code>")

    elif action in ["reject", "decline"]:
        db_exec("UPDATE applications SET status = ? WHERE session_id = ?", ("rejected", session_id))
        answer_callback(callback_id, "❌ Заявка отклонена")
        send_admin(f"❌ <b>Заявка ОТКЛОНЕНА</b>\nСессия: <code>{session_id}</code>")

    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
