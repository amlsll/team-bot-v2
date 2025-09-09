"""
Fallback обработчик для неизвестных сообщений.
"""

from aiogram import Router
from aiogram.types import Message

from ..services.logger import get_logger

logger = get_logger('fallback')
router = Router()


@router.message()
async def handle_unknown_message(message: Message):
    """Обработчик для всех неизвестных сообщений."""
    if not message.from_user:
        return
    
    logger.info(f"📝 Неизвестное сообщение от {message.from_user.id}: {message.text}")
    
    # Проверяем, что это не callback или другое системное сообщение
    if not message.text or message.text.startswith('/'):
        return
    
    # Отправляем пользователю подсказку
    help_text = """Я понимаю только команды:
    
🚀 /start - Начать работу с ботом
📊 /status - Проверить свой статус  
❌ /leave - Покинуть очередь или команду

Выберите одну из команд или нажмите /start для начала работы."""

    await message.reply(help_text)
