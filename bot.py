import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 0))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.id == ADMIN_CHAT_ID:
        await message.answer("✅ Бот работает. Заявки будут приходить сюда.")
    else:
        await message.answer("Этот бот только для администратора.")

# Команда /ping (проверка)
@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    await message.answer("pong")

# Запуск
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
