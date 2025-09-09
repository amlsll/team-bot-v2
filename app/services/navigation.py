"""
Сервис для управления навигацией и кнопками "Назад".
"""

from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class NavigationService:
    """Сервис для создания клавиатур с кнопками навигации."""
    
    @staticmethod
    def add_back_button(
        buttons: List[List[InlineKeyboardButton]], 
        back_callback: str = "go_back"
    ) -> List[List[InlineKeyboardButton]]:
        """Добавляет кнопку 'Назад' в конец списка кнопок."""
        result = buttons.copy()
        result.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_callback)])
        return result
    
    @staticmethod
    def create_keyboard_with_back(
        buttons: List[List[InlineKeyboardButton]], 
        back_callback: str = "go_back"
    ) -> InlineKeyboardMarkup:
        """Создает клавиатуру с кнопками и добавляет кнопку 'Назад'."""
        buttons_with_back = NavigationService.add_back_button(buttons, back_callback)
        return InlineKeyboardMarkup(inline_keyboard=buttons_with_back)
    
    @staticmethod
    def create_simple_keyboard_with_back(
        text_callback_pairs: List[tuple], 
        back_callback: str = "go_back"
    ) -> InlineKeyboardMarkup:
        """Создает простую клавиатуру из пар (текст, callback) с кнопкой 'Назад'."""
        buttons = []
        for text, callback in text_callback_pairs:
            buttons.append([InlineKeyboardButton(text=text, callback_data=callback)])
        
        return NavigationService.create_keyboard_with_back(buttons, back_callback)


# Глобальный экземпляр сервиса навигации
nav = NavigationService()
