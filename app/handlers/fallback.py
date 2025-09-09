"""
Fallback обработчик для неизвестных команд.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..services.logger import get_logger

logger = get_logger('fallback')
router = Router()


@router.message(F.text.startswith('/'))
async def handle_unknown_command(message: Message):
    """Обработчик для неизвестных команд (начинающихся с /)."""
    if not message.from_user:
        return
    
    logger.info(f"❓ Неизвестная команда от {message.from_user.id}: {message.text}")
    
    # Отправляем пользователю подсказку
    help_text = """Я понимаю только эти команды:
    
🚀 /start - Начать работу с ботом
📊 /status - Проверить свой статус  
❌ /leave - Покинуть очередь или команду

Нажмите /start для начала работы."""

    await message.reply(help_text)
