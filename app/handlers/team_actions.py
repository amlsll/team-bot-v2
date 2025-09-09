"""
Обработчики действий в команде: подтверждение участия, отказ.
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from ..services.storage import Storage
from ..services.message_manager import message_manager
from ..services.navigation import nav

router = Router()


@router.callback_query(F.data.startswith("team_confirm:"))
async def callback_team_confirm(callback: CallbackQuery):
    """Обработчик подтверждения участия в команде."""
    if not callback.from_user:
        return
    
    team_id = callback.data.split(":", 1)[1]
    storage = Storage()
    tg_id = callback.from_user.id
    
    # Проверяем, что пользователь действительно в этой команде
    user = storage.get_user(tg_id)
    if not user or user.get('team_id') != team_id:
        await callback.answer("Ошибка: ты не состоишь в этой команде.", show_alert=True)
        return
    
    team = storage.get_team(team_id)
    if not team:
        await callback.answer("Ошибка: команда не найдена.", show_alert=True)
        return
    
    keyboard = nav.create_keyboard_with_back([], "go_back_to_start")
    await message_manager.edit_and_store(callback,
        "✅ Ты подтвердил участие в команде!\n\nОжидай связи от модератора для создания общего чата.",
        reply_markup=keyboard
    )
    await callback.answer("Участие подтверждено!")


@router.callback_query(F.data.startswith("team_decline:"))
async def callback_team_decline(callback: CallbackQuery):
    """Обработчик отказа от участия в команде."""
    if not callback.from_user:
        return
    
    team_id = callback.data.split(":", 1)[1]
    storage = Storage()
    tg_id = callback.from_user.id
    
    # Проверяем, что пользователь действительно в этой команде
    user = storage.get_user(tg_id)
    if not user or user.get('team_id') != team_id:
        await callback.answer("Ошибка: ты не состоишь в этой команде.", show_alert=True)
        return
    
    # Показываем варианты после отказа
    keyboard = nav.create_keyboard_with_back([
        [InlineKeyboardButton(text="Вернуться в лист ожидания", callback_data=f"decline_return:{team_id}")],
        [InlineKeyboardButton(text="Выйти из ожидания", callback_data=f"decline_leave:{team_id}")]
    ], "go_back_to_start")
    
    await message_manager.edit_and_store(callback,
        "Ты отказался от участия в команде.\n\nВыбери дальнейшее действие:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("decline_return:"))
async def callback_decline_return(callback: CallbackQuery):
    """Обработчик возврата в лист ожидания после отказа."""
    if not callback.from_user:
        return
    
    team_id = callback.data.split(":", 1)[1]
    storage = Storage()
    tg_id = callback.from_user.id
    
    # Убираем пользователя из команды
    storage.remove_from_team(team_id, tg_id)
    
    # Возвращаем в статус ожидания и добавляем в очередь
    storage.set_user_status(tg_id, 'waiting', None)
    storage.enqueue(tg_id)
    
    # Получаем информацию для ответа
    from .user_start import get_next_match_time
    queue_count = len(storage.load()['queue'])
    next_match_time = get_next_match_time()
    
    text = f"""Ты возвращен в лист ожидания.

В ожидании сейчас {queue_count} человек.

Ближайшее объединение в команды произойдет {next_match_time}"""
    
    keyboard = nav.create_keyboard_with_back([], "go_back_to_start")
    await message_manager.edit_and_store(callback, text, reply_markup=keyboard)
    await callback.answer("Возвращен в лист ожидания!")


@router.callback_query(F.data.startswith("decline_leave:"))
async def callback_decline_leave(callback: CallbackQuery):
    """Обработчик полного выхода после отказа."""
    if not callback.from_user:
        return
    
    team_id = callback.data.split(":", 1)[1]
    storage = Storage()
    tg_id = callback.from_user.id
    
    # Убираем пользователя из команды
    storage.remove_from_team(team_id, tg_id)
    
    # Убираем из очереди (если был там)
    storage.remove_from_queue(tg_id)
    
    # Можно установить специальный статус или удалить пользователя
    # Пока оставим в статусе waiting, но без очереди
    storage.set_user_status(tg_id, 'waiting', None)
    
    keyboard = nav.create_keyboard_with_back([], "go_back_to_start")
    await message_manager.edit_and_store(callback,
        "Ты вышел из ожидания объединения.\n\nДля повторного участия используй /start",
        reply_markup=keyboard
    )
    await callback.answer("Вышел из ожидания!")
