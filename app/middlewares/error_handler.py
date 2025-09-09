"""
Улучшенный middleware для обработки ошибок и логирования с мониторингом.
"""

import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from ..services.logger import get_logger, log_message, log_callback, log_error, log_timing

logger = get_logger('middleware')

class ErrorHandlerMiddleware(BaseMiddleware):
    """Middleware для глобальной обработки ошибок с детальным логированием."""
    
    def __init__(self):
        super().__init__()
        self.error_count = 0
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        user_id = None
        chat_id = None
        handler_name = None
        
        try:
            # Извлекаем информацию о пользователе и чате
            if hasattr(event, 'from_user') and event.from_user:
                user_id = event.from_user.id
            
            if hasattr(event, 'chat') and event.chat:
                chat_id = event.chat.id
            elif hasattr(event, 'message') and event.message and hasattr(event.message, 'chat'):
                chat_id = event.message.chat.id
            
            # Определяем имя обработчика
            if hasattr(handler, '__name__'):
                handler_name = handler.__name__
            elif hasattr(handler, 'callback') and hasattr(handler.callback, '__name__'):
                handler_name = handler.callback.__name__
            
            # Логируем входящее событие
            if isinstance(event, Message):
                text = getattr(event, 'text', '') or 'non-text'
                logger.debug(f"📩 Получено сообщение от {user_id}: {text[:100]}{'...' if len(text) > 100 else ''}")
                
                # Логируем через систему мониторинга
                log_message(user_id or 0, chat_id or 0, text, handler_name)
                
            elif isinstance(event, CallbackQuery):
                callback_data = getattr(event, 'data', '') or 'no-data'
                logger.debug(f"🔘 Получен callback от {user_id}: {callback_data}")
                
                # Логируем через систему мониторинга
                log_callback(user_id or 0, chat_id or 0, callback_data, handler_name)
            
            # Вызываем обработчик
            result = await handler(event, data)
            
            # Логируем время выполнения
            duration_ms = (time.time() - start_time) * 1000
            log_timing(handler_name or 'unknown_handler', duration_ms, user_id)
            
            if duration_ms > 500:  # Предупреждаем о медленных операциях
                logger.warning(f"⏱️ Медленная обработка: {handler_name} ({duration_ms:.2f}ms)")
            
            return result
            
        except Exception as e:
            self.error_count += 1
            duration_ms = (time.time() - start_time) * 1000
            
            # Создаем контекст для ошибки
            error_context = {
                'handler_name': handler_name,
                'duration_ms': duration_ms,
                'chat_id': chat_id,
                'error_count': self.error_count
            }
            
            if isinstance(event, Message):
                text = getattr(event, 'text', '') or 'non-text'
                error_context['message_text'] = text[:200]
                error_context['event_type'] = 'message'
            elif isinstance(event, CallbackQuery):
                callback_data = getattr(event, 'data', '') or 'no-data'
                error_context['callback_data'] = callback_data
                error_context['event_type'] = 'callback'
            
            # Логируем ошибку через систему мониторинга
            log_error(e, error_context, user_id)
            
            logger.error(f"❌ Ошибка в обработчике #{self.error_count} ({handler_name}): {e}")
            
            # Пытаемся отправить сообщение об ошибке пользователю
            try:
                if isinstance(event, Message):
                    await event.reply(
                        "⚠️ Произошла ошибка при обработке сообщения. "
                        "Попробуйте ещё раз или обратитесь к администратору.\n\n"
                        f"🔍 Код ошибки: #{self.error_count}"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"⚠️ Произошла ошибка (#{self.error_count}). Попробуйте ещё раз.",
                        show_alert=True
                    )
            except Exception as reply_error:
                logger.error(f"❌ Не удалось отправить сообщение об ошибке: {reply_error}")
                log_error(reply_error, {'context': 'error_reply_failed', 'original_error': str(e)}, user_id)
            
            # Не прерываем выполнение, позволяем другим middleware работать
            return None


class PerformanceMiddleware(BaseMiddleware):
    """Middleware для мониторинга производительности."""
    
    def __init__(self, slow_threshold_ms: float = 1000):
        super().__init__()
        self.slow_threshold_ms = slow_threshold_ms
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()
        
        try:
            result = await handler(event, data)
            return result
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # Логируем только медленные операции
            if duration_ms > self.slow_threshold_ms:
                user_id = getattr(event.from_user, 'id', None) if hasattr(event, 'from_user') else None
                handler_name = getattr(handler, '__name__', 'unknown')
                
                logger.warning(
                    f"🐌 Медленная операция: {handler_name} ({duration_ms:.2f}ms)",
                    extra={
                        'handler_name': handler_name,
                        'duration_ms': duration_ms,
                        'user_id': user_id,
                        'threshold_ms': self.slow_threshold_ms
                    }
                )
