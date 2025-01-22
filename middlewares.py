import logging
from aiogram import BaseMiddleware
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)  
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        logger.info(f"Получено сообщение: {event.text}")  # Логирование сообщения
        return await handler(event, data)
