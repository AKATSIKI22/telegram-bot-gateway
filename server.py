import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Ошибка:", e)

@app.route('/submit_credit_application', methods=['POST'])
def submit_application():
    data = request.json
    msg = (
        f"🆕 <b>НОВАЯ ЗАЯВКА</b>\n\n"
        f"👤 ФИО: {data.get('fullname')}\n"
        f"📱 Телефон: {data.get('phone')}\n"
        f"💰 Сумма: {data.get('amount')} BYN\n"
        f"📅 Срок: {data.get('term')} мес"
    )
    send_to_telegram(msg)
    return jsonify({"status": "ok"})

@app.route('/')
def home():
    return "API работает"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
