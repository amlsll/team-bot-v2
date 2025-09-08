"""
Middleware для обработки ошибок и логирования.
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для глобальной обработки ошибок."""
    
    def __init__(self):
        super().__init__()
        self.error_count = 0
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            # Логируем входящее событие
            user_id = None
            if hasattr(event, 'from_user') and event.from_user:
                user_id = event.from_user.id
                
            if isinstance(event, Message):
                text = getattr(event, 'text', 'non-text') or 'empty'
                logger.debug(f"📩 Сообщение от {user_id}: {text}")
            elif isinstance(event, CallbackQuery):
                callback_data = getattr(event, 'data', 'no-data') or 'empty'
                logger.debug(f"🔘 Callback от {user_id}: {callback_data}")
            
            # Вызываем обработчик
            result = await handler(event, data)
            return result
            
        except Exception as e:
            self.error_count += 1
            
            # Логируем ошибку
            logger.error(f"❌ Ошибка в обработчике (#{self.error_count}): {e}")
            
            # Пытаемся отправить сообщение об ошибке пользователю
            try:
                if isinstance(event, Message):
                    await event.reply(
                        "⚠️ Произошла ошибка при обработке сообщения. "
                        "Попробуйте ещё раз или обратитесь к администратору."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "⚠️ Произошла ошибка. Попробуйте ещё раз.",
                        show_alert=True
                    )
            except Exception as reply_error:
                logger.error(f"❌ Не удалось отправить сообщение об ошибке: {reply_error}")
            
            # Не прерываем выполнение, позволяем другим middleware работать
            return None
