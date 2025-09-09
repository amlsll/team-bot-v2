"""
Обработчик команды /status.
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..services.storage import Storage
from ..services.notify import NotificationService
from ..services.message_manager import message_manager
from ..services.navigation import nav

router = Router()


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Обработчик команды /status."""
    if not message.from_user:
        return
    
    storage = Storage()
    notify_service = NotificationService(message.bot)
    tg_id = message.from_user.id
    
    user = storage.get_user(tg_id)
    
    if not user:
        await message_manager.answer_and_store(message, "Ты не зарегистрирован. Используй /start для регистрации.")
        return
    
    if user['status'] == 'waiting':
        # Пользователь в очереди
        position = storage.get_queue_position(tg_id)
        if position == -1:
            await message_manager.answer_and_store(message, "Ты не в очереди. Используй /start и нажми 'Присоединиться'.")
        else:
            from .user_start import get_next_match_time
            queue_count = len(storage.load()['queue'])
            next_match_time = get_next_match_time()
            
            text = f"""В ожидании сейчас {queue_count} человек.

Ближайшее объединение в команды произойдет {next_match_time}"""
            
            keyboard = nav.create_simple_keyboard_with_back([
                ("Выйти из ожидания объединения", "leave")
            ], None)  # Убираем кнопку "Назад" для пользователей в ожидании
            
            await message_manager.answer_and_store(message, text, reply_markup=keyboard)
    
    elif user['status'] == 'teamed':
        # Пользователь в команде
        team_id = user.get('team_id')
        if not team_id:
            await message_manager.answer_and_store(message, "Ошибка: статус 'teamed', но team_id не найден.")
            return
        
        team = storage.get_team(team_id)
        if not team:
            await message_manager.answer_and_store(message, f"Ошибка: команда {team_id} не найдена.")
            return
        
        # Отправляем карточку команды
        text = notify_service.format_team_card(team)
        keyboard = notify_service.get_team_card_keyboard(team_id)
        
        await message_manager.answer_and_store(message, text, reply_markup=keyboard)
    
    else:
        await message_manager.answer_and_store(message, "Неизвестный статус. Обратитесь к администратору.")
