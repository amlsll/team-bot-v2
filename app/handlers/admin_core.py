"""
Основные админские команды: /admin <code>, /logout, ACL.
"""

import os
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from ..services.acl import require_admin, verify_admin_code, is_admin, is_admin_by_env
from ..services.storage import Storage
from ..services.navigation import nav
from ..services.message_manager import message_manager

router = Router()

# Константы для текстов
ADMIN_SUCCESS_TEXT = "Права администратора выданы успешно! 👑"
ADMIN_INVALID_CODE_TEXT = "Неверный код администратора."
LOGOUT_SUCCESS_TEXT = "Права администратора сняты."
LOGOUT_NOT_ADMIN_TEXT = "У тебя нет прав администратора."

def get_admin_panel_text(user_id: int) -> str:
    """Генерирует персонализированный текст админской панели."""
    from datetime import datetime
    storage = Storage()
    sessions = storage.get_admin_sessions()
    
    # Информация о текущей сессии
    current_session = sessions.get(user_id, {})
    login_time = current_session.get('last_login', '')
    login_count = current_session.get('login_count', 0)
    
    if login_time:
        try:
            login_dt = datetime.fromisoformat(login_time)
            login_str = login_dt.strftime('%H:%M')
        except:
            login_str = 'неизвестно'
    else:
        login_str = 'неизвестно'
    
    text = f"""👑 <b>Панель администратора</b>

🔐 Вы вошли в {login_str} (сессия #{login_count})
👥 Активных админов: {len(sessions)}

Выберите действие:"""
    
    return text

ADMIN_PANEL_TEXT = """👑 <b>Панель администратора</b>

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
    
    # Отправляем сообщение об успехе с анимацией
    success_msg = await message.reply("🔐 Проверяю код...")
    await asyncio.sleep(0.5)
    await success_msg.edit_text("✅ Код верный! Получение прав...")
    await asyncio.sleep(0.5)
    await success_msg.edit_text(f"{ADMIN_SUCCESS_TEXT}\n\n🚀 Открываю админскую панель...")
    await asyncio.sleep(1)
    
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
        ("🔐 Сессии", "admin_sessions_view"),
        ("🚪 Выйти из админки", "admin_logout")
    ], None)  # Нет кнопки "Назад" в админской панели
    
    panel_text = get_admin_panel_text(user_id)
    await message_manager.send_and_store(bot, chat_id, panel_text, reply_markup=keyboard)


# Обработчики кнопок админской панели
@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Кнопка статистики."""
    user_id = callback.from_user.id if callback.from_user else None
    import logging
    logging.error(f"🔍 ОТЛАДКА admin_stats: user_id={user_id}")
    
    # Проверяем права напрямую
    from ..services.storage import Storage
    storage = Storage()
    data = storage.load()
    logging.error(f"🔍 ОТЛАДКА: admins в storage = {data.get('admins', {})}")
    logging.error(f"🔍 ОТЛАДКА: is_admin({user_id}) = {is_admin(user_id) if user_id else False}")
    
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        from .admin_stats import get_stats_response
        
        # Получаем текст статистики напрямую
        response = await get_stats_response()
        await message_manager.edit_and_store(callback, response)
        await callback.answer()
        
    except Exception as e:
        import logging
        logging.error(f"❌ Ошибка в admin_stats callback: {e}")
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


@router.callback_query(F.data == "admin_rematch_input")
async def callback_admin_rematch_input(callback: CallbackQuery):
    """Кнопка расформирования команды - запрос ID команды."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        text = """💥 **Расформирование команды**

Введите ID команды для расформирования:
Формат: `/adm_rematch team_id [--front]`

Опции:
• `--front` - добавить участников в начало очереди

Пример: `/adm_rematch TEAM_001 --front`"""
        
        # Добавляем кнопку возврата к панели
        keyboard = nav.create_simple_keyboard_with_back([
            ("🏠 Вернуться к панели", "back_to_admin_panel")
        ], None)
        
        await message_manager.edit_and_store(callback, text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_broadcast_input")
async def callback_admin_broadcast_input(callback: CallbackQuery):
    """Кнопка рассылки - инструкция по использованию."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        text = """📢 **Рассылка сообщений**

Для отправки рассылки используйте команду:
`/adm_broadcast <текст сообщения>`

Пример:
`/adm_broadcast Привет всем! Новости от организаторов.`

После отправки команды вы сможете выбрать аудиторию:
• Ожидающим в очереди
• Участникам команд"""
        
        # Добавляем кнопку возврата к панели
        keyboard = nav.create_simple_keyboard_with_back([
            ("🏠 Вернуться к панели", "back_to_admin_panel")
        ], None)
        
        await message_manager.edit_and_store(callback, text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_update_check")
async def callback_admin_update_check(callback: CallbackQuery):
    """Кнопка проверки обновлений."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        from .auto_update import cmd_check_updates
        # Создаем mock сообщение для вызова команды
        class MockMessage:
            def __init__(self, callback_query):
                self.from_user = callback_query.from_user
                self.chat = callback_query.message.chat
                self.text = "/adm_update_check"
                self.bot = callback_query.bot
            
            async def reply(self, text, **kwargs):
                return await message_manager.edit_and_store(callback, text, **kwargs)
        
        mock_message = MockMessage(callback)
        await cmd_check_updates(mock_message)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_update_apply")
async def callback_admin_update_apply(callback: CallbackQuery):
    """Кнопка применения обновлений."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        from .auto_update import cmd_apply_updates
        # Создаем mock сообщение для вызова команды
        class MockMessage:
            def __init__(self, callback_query):
                self.from_user = callback_query.from_user
                self.chat = callback_query.message.chat
                self.text = "/adm_update_apply"
                self.bot = callback_query.bot
            
            async def reply(self, text, **kwargs):
                return await message_manager.edit_and_store(callback, text, **kwargs)
        
        mock_message = MockMessage(callback)
        await cmd_apply_updates(mock_message)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_restart")
async def callback_admin_restart(callback: CallbackQuery):
    """Кнопка перезапуска бота."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        from .admin_restart import cmd_restart_bot
        # Создаем mock сообщение для вызова команды
        class MockMessage:
            def __init__(self, callback_query):
                self.from_user = callback_query.from_user
                self.chat = callback_query.message.chat
                self.text = "/adm_restart"
                self.bot = callback_query.bot
            
            async def reply(self, text, **kwargs):
                return await message_manager.edit_and_store(callback, text, **kwargs)
        
        mock_message = MockMessage(callback)
        await cmd_restart_bot(mock_message)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_system_status")
async def callback_admin_system_status(callback: CallbackQuery):
    """Кнопка статуса системы."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        from .admin_restart import cmd_bot_status
        # Создаем mock сообщение для вызова команды
        class MockMessage:
            def __init__(self, callback_query):
                self.from_user = callback_query.from_user
                self.chat = callback_query.message.chat
                self.text = "/adm_status"
                self.bot = callback_query.bot
            
            async def reply(self, text, **kwargs):
                return await message_manager.edit_and_store(callback, text, **kwargs)
        
        mock_message = MockMessage(callback)
        await cmd_bot_status(mock_message)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "admin_sessions_view")
async def callback_admin_sessions_view(callback: CallbackQuery):
    """Кнопка просмотра сессий."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        storage = Storage()
        sessions = storage.get_admin_sessions()
        
        if not sessions:
            text = "🔐 **Активные сессии**\n\nНет активных админских сессий"
            keyboard = nav.create_simple_keyboard_with_back([
                ("🏠 К панели", "back_to_admin_panel")
            ], None)
        else:
            from datetime import datetime
            text = "🔐 **Активные админские сессии:**\n\n"
            
            for tg_id, info in sessions.items():
                last_login = info.get('last_login', 'неизвестно')
                login_count = info.get('login_count', 0)
                
                if last_login != 'неизвестно':
                    try:
                        login_dt = datetime.fromisoformat(last_login)
                        last_login_str = login_dt.strftime('%d.%m %H:%M')
                    except:
                        last_login_str = last_login
                else:
                    last_login_str = 'неизвестно'
                
                # Проверяем, это ли текущий пользователь
                current_mark = " (это вы)" if tg_id == callback.from_user.id else ""
                
                text += f"👤 **ID {tg_id}**{current_mark}\n"
                text += f"• Вход: {last_login_str}\n"
                text += f"• Сессий: {login_count}\n\n"
            
            keyboard = nav.create_simple_keyboard_with_back([
                ("🚪 Завершить все", "logout_all_sessions"),
                ("🏠 К панели", "back_to_admin_panel")
            ], None)
        
        await message_manager.edit_and_store(callback, text, reply_markup=keyboard)
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


# Быстрая команда для доступа к админ панели
@router.message(Command("ap"))
@require_admin
async def cmd_admin_panel_quick(message: Message):
    """Быстрый доступ к админской панели."""
    if not message.from_user:
        return
    
    await show_admin_panel(message.bot, message.chat.id, message.from_user.id)


# Быстрые команды для частых действий
@router.message(Command("qs"))  # Quick Stats
@require_admin
async def cmd_quick_stats(message: Message):
    """Быстрая статистика."""
    if not message.from_user:
        return
    
    try:
        from .admin_stats import cmd_adm_stats
        await cmd_adm_stats(message)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("qm"))  # Quick Match
@require_admin
async def cmd_quick_match(message: Message):
    """Быстрый матчинг."""
    if not message.from_user:
        return
    
    try:
        from .admin_match import cmd_adm_match
        await cmd_adm_match(message)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@router.message(Command("help_admin"))
@require_admin
async def cmd_admin_help(message: Message):
    """Справка по админским командам."""
    help_text = """🔧 **Справка по админским командам**

📋 **Основные команды:**
• `/admin <код>` — авторизация
• `/ap` — админская панель
• `/logout` — выход из админки

⚡ **Быстрые команды:**
• `/qs` — быстрая статистика
• `/qm` — быстрый матчинг
• `/admin_sessions` — активные сессии

🛠️ **Полные команды:**
• `/adm_stats` — подробная статистика
• `/adm_match` — провести матчинг
• `/adm_broadcast <текст>` — рассылка
• `/adm_rematch <id> [--front]` — расформировать
• `/adm_restart` — перезапуск бота
• `/adm_status` — статус системы

🔍 **Диагностика:**
• `/admin_debug` — диагностика прав
• `/health` — проверка здоровья
• `/metrics` — метрики производительности"""
    
    await message.reply(help_text)


@router.message(Command("admin_debug"))
async def cmd_admin_debug(message: Message):
    """Диагностическая команда для отладки проблем с админкой."""
    if not message.from_user:
        return
    
    tg_id = message.from_user.id
    
    # Проверяем все возможные источники прав
    is_admin_env = is_admin_by_env(tg_id)
    
    storage = Storage()
    is_admin_storage = storage.is_admin(tg_id)
    is_admin_final = is_admin(tg_id)
    
    # Проверяем настройки
    admin_code_set = bool(os.getenv('ADMIN_CODE', ''))
    admins_env = os.getenv('ADMINS', '')
    
    debug_text = f"""🔍 **Диагностика админских прав**

👤 **Ваш ID:** `{tg_id}`

🔐 **Права доступа:**
• Из переменной ADMINS: {'✅' if is_admin_env else '❌'}
• Из runtime storage: {'✅' if is_admin_storage else '❌'}
• Итоговый результат: {'✅' if is_admin_final else '❌'}

⚙️ **Настройки:**
• ADMIN_CODE установлен: {'✅' if admin_code_set else '❌'}
• ADMINS в env: `{admins_env if admins_env else 'не установлено'}`

💡 **Как получить права:**
1. Задайте ADMIN_CODE в .env файле
2. Используйте /admin <ваш_код>
3. Или добавьте ваш ID в ADMINS в .env"""
    
    await message.reply(debug_text)


@router.message(Command("admin_sessions"))
@require_admin
async def cmd_admin_sessions(message: Message):
    """Показывает активные админские сессии."""
    if not message.from_user:
        return
    
    storage = Storage()
    sessions = storage.get_admin_sessions()
    
    if not sessions:
        await message.reply("🔐 Нет активных админских сессий")
        return
    
    from datetime import datetime
    text = "🔐 **Активные админские сессии:**\n\n"
    
    for tg_id, info in sessions.items():
        last_login = info.get('last_login', 'неизвестно')
        login_count = info.get('login_count', 0)
        
        if last_login != 'неизвестно':
            try:
                login_dt = datetime.fromisoformat(last_login)
                last_login_str = login_dt.strftime('%d.%m.%Y %H:%M')
            except:
                last_login_str = last_login
        else:
            last_login_str = 'неизвестно'
        
        # Проверяем, это ли текущий пользователь
        current_mark = " (это вы)" if tg_id == message.from_user.id else ""
        
        text += f"👤 **ID {tg_id}**{current_mark}\n"
        text += f"• Последний вход: {last_login_str}\n"
        text += f"• Всего входов: {login_count}\n\n"
    
    # Добавляем кнопку для завершения всех сессий
    keyboard = nav.create_simple_keyboard_with_back([
        ("🚪 Завершить все сессии", "logout_all_sessions"),
        ("🏠 К панели", "back_to_admin_panel")
    ], None)
    
    await message.reply(text, reply_markup=keyboard)


@router.callback_query(F.data == "logout_all_sessions")
async def callback_logout_all_sessions(callback: CallbackQuery):
    """Завершает все админские сессии."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        storage = Storage()
        store = storage.load()
        
        # Завершаем все сессии
        for tg_id in list(store['admins'].keys()):
            storage.set_admin(tg_id, False)
        
        await message_manager.edit_and_store(callback, "🚪 Все админские сессии завершены.\n\nДля повторного входа используйте /admin <код>")
        await callback.answer("Все сессии завершены")
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "back_to_admin_panel")
async def callback_back_to_admin_panel(callback: CallbackQuery):
    """Возврат к главной админской панели."""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("Нет прав доступа", show_alert=True)
        return
    
    try:
        # Редактируем сообщение и показываем админскую панель
        keyboard = nav.create_simple_keyboard_with_back([
            ("📊 Статистика", "admin_stats"),
            ("🔄 Провести матчинг", "admin_match"),
            ("💥 Расформировать команду", "admin_rematch_input"),
            ("📢 Рассылка", "admin_broadcast_input"),
            ("🔄 Проверить обновления", "admin_update_check"),
            ("🔧 Применить обновления", "admin_update_apply"),
            ("🔄 Перезапустить бота", "admin_restart"),
            ("ℹ️ Статус системы", "admin_system_status"),
            ("🔐 Сессии", "admin_sessions_view"),
            ("🚪 Выйти из админки", "admin_logout")
        ], None)
        
        panel_text = get_admin_panel_text(callback.from_user.id)
        await message_manager.edit_and_store(callback, panel_text, reply_markup=keyboard)
        await callback.answer("🏠 Возвращаемся к панели управления")
        
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


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
