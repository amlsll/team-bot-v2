"""
Основные админские команды: /admin <code>, /logout, ACL.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from ..services.acl import require_admin, verify_admin_code, is_admin
from ..services.storage import Storage
from ..services.navigation import nav
from ..services.message_manager import message_manager

router = Router()

# Константы для текстов
ADMIN_SUCCESS_TEXT = "Права администратора выданы успешно! 👑"
ADMIN_INVALID_CODE_TEXT = "Неверный код администратора."
LOGOUT_SUCCESS_TEXT = "Права администратора сняты."
LOGOUT_NOT_ADMIN_TEXT = "У тебя нет прав администратора."

ADMIN_PANEL_TEXT = """👑 **Панель администратора**

Выберите действие:"""


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin <code>."""
    if not message.from_user:
        return
    
    # Извлекаем код из аргументов команды
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /admin <код>")
        return
    
    code = args[1]
    tg_id = message.from_user.id
    
    # Проверяем код
    if not verify_admin_code(code):
        await message.reply(ADMIN_INVALID_CODE_TEXT)
        return
    
    # Выдаем права
    storage = Storage()
    storage.set_admin(tg_id, True)
    
    # Показываем админскую панель
    await show_admin_panel(message.bot, message.chat.id, tg_id)


@router.message(Command("logout"))
async def cmd_logout(message: Message):
    """Обработчик команды /logout."""
    if not message.from_user:
        return
    
    tg_id = message.from_user.id
    
    # Проверяем, есть ли права
    if not is_admin(tg_id):
        await message.reply(LOGOUT_NOT_ADMIN_TEXT)
        return
    
    # Снимаем права (только runtime, не из env)
    storage = Storage()
    storage.set_admin(tg_id, False)
    
    await message.reply(LOGOUT_SUCCESS_TEXT)


async def show_admin_panel(bot, chat_id: int, user_id: int):
    """Показывает админскую панель с кнопками управления."""
    keyboard = nav.create_simple_keyboard_with_back([
        ("📊 Статистика", "admin_stats"),
        ("🔄 Провести матчинг", "admin_match"),
        ("💥 Расформировать команду", "admin_rematch_input"),
        ("📢 Рассылка", "admin_broadcast_input"),
        ("🔄 Проверить обновления", "admin_update_check"),
        ("🔧 Применить обновления", "admin_update_apply"),
        ("🔄 Перезапустить бота", "admin_restart"),
        ("ℹ️ Статус системы", "admin_system_status"),
        ("🚪 Выйти из админки", "admin_logout")
    ], None)  # Нет кнопки "Назад" в админской панели
    
    await message_manager.send_and_store(bot, chat_id, ADMIN_PANEL_TEXT, reply_markup=keyboard)


# Обработчики кнопок админской панели
@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Кнопка статистики."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        from .admin_stats import cmd_adm_stats
        # Создаем mock сообщение для вызова команды
        class MockMessage:
            def __init__(self, callback_query):
                self.from_user = callback_query.from_user
                self.chat = callback_query.message.chat
                self.text = "/adm_stats"
                self.bot = callback_query.bot
            
            async def reply(self, text, **kwargs):
                return await message_manager.edit_and_store(callback, text, **kwargs)
        
        mock_message = MockMessage(callback)
        await cmd_adm_stats(mock_message)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_match")
async def callback_admin_match(callback: CallbackQuery):
    """Кнопка проведения матчинга."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        from .admin_match import cmd_adm_match
        # Создаем mock сообщение для вызова команды
        class MockMessage:
            def __init__(self, callback_query):
                self.from_user = callback_query.from_user
                self.chat = callback_query.message.chat
                self.text = "/adm_match"
                self.bot = callback_query.bot
            
            async def reply(self, text, **kwargs):
                return await message_manager.edit_and_store(callback, text, **kwargs)
        
        mock_message = MockMessage(callback)
        await cmd_adm_match(mock_message)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_logout")
async def callback_admin_logout(callback: CallbackQuery):
    """Кнопка выхода из админки."""
    if not callback.from_user:
        return
    
    tg_id = callback.from_user.id
    
    if not is_admin(tg_id):
        await message_manager.edit_and_store(callback, LOGOUT_NOT_ADMIN_TEXT)
        await callback.answer()
        return
    
    storage = Storage()
    storage.set_admin(tg_id, False)
    
    await message_manager.edit_and_store(callback, LOGOUT_SUCCESS_TEXT)
    await callback.answer()


# Команда для показа админской панели
@router.message(Command("admin_panel"))
@require_admin
async def cmd_admin_panel(message: Message):
    """Показывает админскую панель."""
    if not message.from_user:
        return
    
    await show_admin_panel(message.bot, message.chat.id, message.from_user.id)


# Обработчики callback'ов от карточек команд
@router.callback_query(F.data.startswith("team_confirm:"))
async def callback_team_confirm(callback: CallbackQuery):
    """Обработчик нажатия кнопки 'Я в команде ✅'."""
    team_id = callback.data.split(":", 1)[1]
    
    await callback.answer("Отлично! Удачи в команде! 🚀")
    
    # Можно добавить логику отметки подтверждения участия


@router.callback_query(F.data.startswith("team_problem:"))
async def callback_team_problem(callback: CallbackQuery):
    """Обработчик нажатия кнопки 'Проблема/замена'."""
    if not callback.from_user:
        return
    
    team_id = callback.data.split(":", 1)[1]
    username = callback.from_user.username or "без_username"
    
    # Отправляем репорт модераторам
    from ..services.notify import NotificationService
    notify_service = NotificationService(callback.bot)
    
    report_text = f"🚨 Проблема с командой {team_id}\n\nПользователь: @{username} (ID: {callback.from_user.id})"
    
    success = await notify_service.send_to_moderators(report_text)
    
    if success:
        await callback.answer("Сообщение отправлено модераторам. Ожидайте ответа.")
    else:
        await callback.answer("Не удалось отправить сообщение. Обратитесь к организаторам напрямую.")
