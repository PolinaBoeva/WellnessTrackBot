import logging
import asyncio
from aiogram import Bot, Dispatcher
from config import Config  # Ваш токен
from handlers import setup_handlers  # Ваши обработчики
from middlewares import LoggingMiddleware  # Ваш middleware

logging.basicConfig(level=logging.INFO)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=Config().BOT_TOKEN)
dp = Dispatcher()

# Настраиваем middleware и обработчики
dp.message.middleware(LoggingMiddleware())
setup_handlers(dp)

async def main():
    print("Бот запущен!")
    await bot.delete_webhook()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())