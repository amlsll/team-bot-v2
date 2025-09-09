"""
Обработчик команды /leave с подтверждением.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from ..services.storage import Storage
from ..services.message_manager import message_manager
from ..services.navigation import nav

router = Router()

# Константы для текстов
LEAVE_CONFIRM_TEXT = "Точно выйти?"
LEAVE_SUCCESS_QUEUE_TEXT = "Вы вышли из очереди."
LEAVE_SUCCESS_TEAM_TEXT = "Ты вышел из команды и возвращен в статус ожидания."
LEAVE_CANCELLED_TEXT = "Отмена выхода."


@router.message(Command("leave"))
async def cmd_leave(message: Message):
    """Обработчик команды /leave."""
    if not message.from_user:
        return
    
    storage = Storage()
    tg_id = message.from_user.id
    
    user = storage.get_user(tg_id)
    if not user:
        await message_manager.answer_and_store(message, "Ты не зарегистрирован.")
        return
    
    # Проверяем, есть ли что покидать
    in_queue = storage.get_queue_position(tg_id) != -1
    in_team = user['status'] == 'teamed' and user.get('team_id')
    
    if not in_queue and not in_team:
        await message_manager.answer_and_store(message, "Ты не в очереди и не в команде.")
        return
    
    # Показываем подтверждение
    keyboard = nav.create_keyboard_with_back([
        [
            InlineKeyboardButton(text="Да", callback_data="leave_confirm"),
            InlineKeyboardButton(text="Нет", callback_data="leave_cancel")
        ]
    ], None)  # Убираем кнопку "Назад" для избежания рекурсии
    
    await message_manager.answer_and_store(message, LEAVE_CONFIRM_TEXT, reply_markup=keyboard)


@router.callback_query(F.data == "leave_confirm")
async def callback_leave_confirm(callback: CallbackQuery):
    """Обработчик подтверждения выхода."""
    if not callback.from_user:
        return
    
    storage = Storage()
    tg_id = callback.from_user.id
    
    user = storage.get_user(tg_id)
    if not user:
        await message_manager.edit_and_store(callback, "Ошибка: пользователь не найден.")
        return
    
    # Убираем из очереди
    removed_from_queue = storage.remove_from_queue(tg_id)
    
    # Убираем из команды, если был в команде
    if user['status'] == 'teamed' and user.get('team_id'):
        team_id = user['team_id']
        storage.remove_from_team(team_id, tg_id)
        storage.set_user_status(tg_id, 'waiting', None)
        
        keyboard = nav.create_keyboard_with_back([], None)  # Убираем кнопку "Назад"
        await message_manager.edit_and_store(callback, LEAVE_SUCCESS_TEAM_TEXT, reply_markup=keyboard)
    elif removed_from_queue:
        # После выхода из очереди показываем стартовый экран
        from .user_start import show_registered_user_start_screen
        success = await show_registered_user_start_screen(callback.message, tg_id)
        if not success:
            # Если не удалось показать стартовый экран, показываем простое сообщение
            keyboard = nav.create_keyboard_with_back([], None)  # Убираем кнопку "Назад" 
            await message_manager.edit_and_store(callback, LEAVE_SUCCESS_QUEUE_TEXT, reply_markup=keyboard)
    else:
        keyboard = nav.create_keyboard_with_back([], None)  # Убираем кнопку "Назад"
        await message_manager.edit_and_store(callback, "Ты не был в очереди или команде.", reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(F.data == "leave_cancel")
async def callback_leave_cancel(callback: CallbackQuery):
    """Обработчик отмены выхода."""
    keyboard = nav.create_keyboard_with_back([], None)  # Убираем кнопку "Назад"
    await message_manager.edit_and_store(callback, LEAVE_CANCELLED_TEXT, reply_markup=keyboard)
    await callback.answer()
