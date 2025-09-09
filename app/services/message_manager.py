"""
Менеджер сообщений для автоматического удаления старых сообщений бота.
"""

import logging
from typing import Dict, Optional, List
from aiogram.types import Message, CallbackQuery
from .storage import Storage

logger = logging.getLogger(__name__)


class MessageManager:
    """Класс для управления сообщениями бота и их автоматического удаления."""
    
    def __init__(self):
        self.storage = Storage()
        
    def _get_user_messages_key(self, user_id: int) -> str:
        """Возвращает ключ для хранения сообщений пользователя."""
        return f"user_messages_{user_id}"
    
    def store_message(self, user_id: int, message_id: int) -> None:
        """Сохраняет ID сообщения бота для пользователя."""
        try:
            store = self.storage.load()
            key = self._get_user_messages_key(user_id)
            
            # Инициализируем список сообщений если его нет
            if 'user_messages' not in store:
                store['user_messages'] = {}
            
            if key not in store['user_messages']:
                store['user_messages'][key] = []
            
            # Добавляем новое сообщение
            store['user_messages'][key].append(message_id)
            
            # Ограничиваем количество сохраняемых сообщений (последние 10)
            if len(store['user_messages'][key]) > 10:
                store['user_messages'][key] = store['user_messages'][key][-10:]
            
            self.storage.save(store)
            logger.debug(f"Сохранен message_id {message_id} для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении message_id {message_id} для пользователя {user_id}: {e}")
    
    def get_user_messages(self, user_id: int) -> List[int]:
        """Получает список ID сообщений пользователя."""
        try:
            store = self.storage.load()
            key = self._get_user_messages_key(user_id)
            
            if 'user_messages' not in store:
                return []
                
            return store['user_messages'].get(key, [])
            
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений пользователя {user_id}: {e}")
            return []
    
    def clear_user_messages(self, user_id: int) -> None:
        """Очищает список сообщений пользователя."""
        try:
            store = self.storage.load()
            key = self._get_user_messages_key(user_id)
            
            if 'user_messages' in store and key in store['user_messages']:
                store['user_messages'][key] = []
                self.storage.save(store)
                logger.debug(f"Очищены сообщения для пользователя {user_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке сообщений пользователя {user_id}: {e}")
    
    async def delete_previous_messages(self, bot, user_id: int, chat_id: int, exclude_message_id: Optional[int] = None) -> None:
        """Удаляет все предыдущие сообщения бота для пользователя."""
        message_ids = self.get_user_messages(user_id)
        
        for message_id in message_ids:
            # Пропускаем сообщение, которое исключено
            if exclude_message_id and message_id == exclude_message_id:
                continue
                
            try:
                await bot.delete_message(chat_id, message_id)
                logger.debug(f"Удалено сообщение {message_id} для пользователя {user_id}")
            except Exception as e:
                # Игнорируем ошибки удаления (сообщение может быть уже удалено)
                logger.debug(f"Не удалось удалить сообщение {message_id} для пользователя {user_id}: {e}")
        
        # Очищаем список после удаления (кроме исключенного сообщения)
        if exclude_message_id:
            # Сохраняем только исключенное сообщение
            store = self.storage.load()
            key = self._get_user_messages_key(user_id)
            if 'user_messages' in store and key in store['user_messages']:
                store['user_messages'][key] = [exclude_message_id]
                self.storage.save(store)
        else:
            self.clear_user_messages(user_id)
    
    async def send_and_store(self, bot, chat_id: int, text: str, **kwargs) -> Optional[Message]:
        """Отправляет сообщение и сохраняет его ID для последующего удаления."""
        try:
            # Отправляем новое сообщение
            message = await bot.send_message(chat_id, text, **kwargs)
            
            # Удаляем предыдущие сообщения (кроме только что отправленного)
            await self.delete_previous_messages(bot, chat_id, chat_id, exclude_message_id=message.message_id)
            
            # Сохраняем ID нового сообщения
            self.store_message(chat_id, message.message_id)
            
            return message
            
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")
            return None
    
    async def edit_and_store(self, message_or_callback, text: str, **kwargs) -> Optional[Message]:
        """Редактирует сообщение и обновляет его в хранилище."""
        try:
            if isinstance(message_or_callback, CallbackQuery):
                # Это callback query
                if not message_or_callback.message:
                    return None
                    
                user_id = message_or_callback.from_user.id if message_or_callback.from_user else None
                chat_id = message_or_callback.message.chat.id
                
                # Редактируем сообщение
                edited_message = await message_or_callback.message.edit_text(text, **kwargs)
                
                # Обновляем ID сообщения в хранилище (если user_id доступен)
                if user_id:
                    # Удаляем старые сообщения кроме текущего
                    await self.delete_previous_messages(message_or_callback.bot, user_id, chat_id, exclude_message_id=edited_message.message_id)
                    # Сохраняем ID текущего сообщения (если его еще нет)
                    current_messages = self.get_user_messages(user_id)
                    if edited_message.message_id not in current_messages:
                        self.store_message(user_id, edited_message.message_id)
                
                return edited_message
                
            else:
                # Это обычное сообщение
                user_id = message_or_callback.from_user.id if message_or_callback.from_user else None
                chat_id = message_or_callback.chat.id
                
                # Редактируем сообщение
                edited_message = await message_or_callback.edit_text(text, **kwargs)
                
                # Обновляем ID сообщения в хранилище (если user_id доступен)
                if user_id:
                    # Удаляем старые сообщения кроме текущего
                    await self.delete_previous_messages(message_or_callback.bot, user_id, chat_id, exclude_message_id=edited_message.message_id)
                    # Сохраняем ID текущего сообщения (если его еще нет)
                    current_messages = self.get_user_messages(user_id)
                    if edited_message.message_id not in current_messages:
                        self.store_message(user_id, edited_message.message_id)
                
                return edited_message
                
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            return None
    
    async def answer_and_store(self, message, text: str, **kwargs) -> Optional[Message]:
        """Отвечает на сообщение и сохраняет ID ответа."""
        try:
            user_id = message.from_user.id if message.from_user else None
            chat_id = message.chat.id
            
            # Удаляем предыдущие сообщения
            if user_id:
                await self.delete_previous_messages(message.bot, user_id, chat_id)
            
            # Отправляем ответ
            reply_message = await message.reply(text, **kwargs)
            
            # Сохраняем ID ответа
            if user_id:
                self.store_message(user_id, reply_message.message_id)
            
            return reply_message
            
        except Exception as e:
            logger.error(f"Ошибка при ответе на сообщение: {e}")
            return None


# Глобальный экземпляр менеджера сообщений
message_manager = MessageManager()
