"""
Основные админские команды: /admin <code>, /logout, ACL.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from ..services.acl import require_admin, verify_admin_code, is_admin
from ..services.storage import Storage

router = Router()

# Константы для текстов
ADMIN_SUCCESS_TEXT = "Права администратора выданы успешно! 👑"
ADMIN_INVALID_CODE_TEXT = "Неверный код администратора."
LOGOUT_SUCCESS_TEXT = "Права администратора сняты."
LOGOUT_NOT_ADMIN_TEXT = "У тебя нет прав администратора."


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
    
    await message.reply(ADMIN_SUCCESS_TEXT)


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
