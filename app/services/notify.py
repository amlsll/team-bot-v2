"""
Сервис для отправки уведомлений и форматирования карточек команд.
"""

import os
from typing import List, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from ..types import Team
from .storage import Storage
from .navigation import nav


class NotificationService:
    """Сервис для отправки уведомлений пользователям."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.storage = Storage()
    
    def format_team_card(self, team: Team) -> str:
        """
        Форматирует карточку команды для отправки пользователям.
        
        Args:
            team: Данные команды
            
        Returns:
            Отформатированный текст карточки
        """
        # Получаем информацию об участниках
        members_list = []
        for i, tg_id in enumerate(team['members']):
            user = self.storage.get_user(tg_id)
            
            # Используем введенное пользователем имя и ссылку, если есть
            if user and user.get('full_name') and user.get('telegram_link'):
                name = user['full_name']
                link = user['telegram_link']
            elif user and user.get('username'):
                name = user.get('name', f"User{tg_id}")
                link = f"@{user['username']}"
            else:
                name = f"User{tg_id}"
                link = f"ID:{tg_id}"
            
            # Отмечаем модератора (первый в списке)
            if i == 0:
                members_list.append(f"{i+1}. {name}, {link} (модератор)")
            else:
                members_list.append(f"{i+1}. {name}, {link}")
        
        text = f"""Поздравляем тебя со вступлением в команду.

{chr(10).join(members_list)}

Участник с ролью модератора должен связаться со всеми остальными участниками из списка и организовать групповой чат до 19:00 следующего дня, чтобы в дальнейшем подать заявку на участие в конкурсе."""
        
        return text
    
    def get_team_card_keyboard(self, team_id: str) -> InlineKeyboardMarkup:
        """Создает клавиатуру для карточки команды."""
        buttons = [
            [InlineKeyboardButton(text="Я подтверждаю участие", callback_data=f"team_confirm:{team_id}")],
            [InlineKeyboardButton(text="Отказываюсь от участия", callback_data=f"team_decline:{team_id}")]
        ]
        
        return nav.create_keyboard_with_back(buttons, "go_back_to_start")
    
    async def send_team_card_to_members(self, team: Team) -> None:
        """
        Отправляет карточку команды всем её участникам.
        
        Args:
            team: Данные команды
        """
        text = self.format_team_card(team)
        keyboard = self.get_team_card_keyboard(team['id'])
        
        for tg_id in team['members']:
            try:
                await self.bot.send_message(
                    chat_id=tg_id,
                    text=text,
                    reply_markup=keyboard
                )
            except (TelegramForbiddenError, TelegramBadRequest):
                # Пользователь заблокировал бота или удалил аккаунт
                # В продакшене здесь можно логировать или уведомлять админов
                pass
    
    async def broadcast_to_waiting(self, text: str) -> int:
        """
        Рассылает сообщение всем ожидающим в очереди.
        
        Args:
            text: Текст сообщения
            
        Returns:
            Количество успешно доставленных сообщений
        """
        store = self.storage.load()
        sent_count = 0
        
        for tg_id in store['queue']:
            try:
                await self.bot.send_message(chat_id=tg_id, text=text)
                sent_count += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                pass
        
        return sent_count
    
    async def broadcast_to_teams(self, text: str) -> int:
        """
        Рассылает сообщение всем участникам активных команд.
        
        Args:
            text: Текст сообщения
            
        Returns:
            Количество успешно доставленных сообщений
        """
        store = self.storage.load()
        sent_count = 0
        sent_to = set()  # Избегаем дублей
        
        for team in store['teams'].values():
            if team['status'] == 'active':
                for tg_id in team['members']:
                    if tg_id not in sent_to:
                        try:
                            await self.bot.send_message(chat_id=tg_id, text=text)
                            sent_count += 1
                            sent_to.add(tg_id)
                        except (TelegramForbiddenError, TelegramBadRequest):
                            pass
        
        return sent_count
    
    async def send_to_moderators(self, text: str) -> bool:
        """
        Отправляет сообщение в чат модераторов.
        
        Args:
            text: Текст сообщения
            
        Returns:
            True, если сообщение отправлено успешно
        """
        mod_chat_id = os.getenv('MOD_CHAT_ID')
        if not mod_chat_id:
            return False
        
        try:
            await self.bot.send_message(chat_id=mod_chat_id, text=text)
            return True
        except (TelegramForbiddenError, TelegramBadRequest):
            return False
