import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

@app.route('/')
def home():
    return "✅ API работает"

@app.route('/submit_credit_application', methods=['POST'])
def submit():
    data = request.json
    text = f"🆕 Новая заявка\n\n👤 {data.get('fullname')}\n📱 {data.get('phone')}\n💰 {data.get('amount')} BYN"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text})
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
