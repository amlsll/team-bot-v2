"""
Админская команда /adm_change для возврата пользователя в лист ожидания.
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..services.acl import require_admin
from ..services.storage import Storage

router = Router()


@router.message(Command("adm_change"))
@require_admin
async def cmd_adm_change(message: Message):
    """Админская команда для возврата пользователя в лист ожидания."""
    # Извлекаем аргументы команды
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /adm_change Имя Фамилия\n\nПример: /adm_change Иван Иванов")
        return
    
    search_name = args[1].strip()
    storage = Storage()
    
    # Ищем пользователя по полному имени
    store = storage.load()
    found_users = []
    
    for tg_id, user in store['users'].items():
        if user.get('full_name') and search_name.lower() in user['full_name'].lower():
            found_users.append((tg_id, user))
    
    if not found_users:
        await message.reply(f"Пользователь с именем '{search_name}' не найден.")
        return
    
    if len(found_users) > 1:
        # Если найдено несколько пользователей, показываем список
        response = f"Найдено несколько пользователей с именем '{search_name}':\n\n"
        for tg_id, user in found_users:
            status_text = "в команде" if user['status'] == 'teamed' else "в очереди" if user['status'] == 'waiting' else "неизвестен"
            response += f"• {user.get('full_name', 'Без имени')} (@{user.get('username', 'без username')}) - {status_text}\n"
            response += f"  ID: {tg_id}\n\n"
        
        response += "Используйте команду: /adm_change_id <tg_id> для точного выбора"
        await message.reply(response)
        return
    
    # Найден один пользователь
    tg_id, user = found_users[0]
    result = await _return_user_to_queue(storage, tg_id, user)
    await message.reply(result)


@router.message(Command("adm_change_id"))
@require_admin
async def cmd_adm_change_id(message: Message):
    """Админская команда для возврата пользователя в лист ожидания по ID."""
    # Извлекаем аргументы команды
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /adm_change_id <tg_id>\n\nПример: /adm_change_id 123456789")
        return
    
    try:
        tg_id = int(args[1])
    except ValueError:
        await message.reply("Ошибка: введите корректный числовой ID пользователя.")
        return
    
    storage = Storage()
    user = storage.get_user(tg_id)
    
    if not user:
        await message.reply(f"Пользователь с ID {tg_id} не найден.")
        return
    
    result = await _return_user_to_queue(storage, tg_id, user)
    await message.reply(result)


async def _return_user_to_queue(storage: Storage, tg_id: int, user: dict) -> str:
    """Вспомогательная функция для возврата пользователя в очередь."""
    user_name = user.get('full_name', f"ID:{tg_id}")
    
    if user['status'] == 'waiting':
        # Пользователь уже в ожидании, проверяем очередь
        queue_position = storage.get_queue_position(tg_id)
        if queue_position == -1:
            # Не в очереди, добавляем
            storage.enqueue(tg_id)
            return f"✅ Пользователь {user_name} добавлен в очередь ожидания."
        else:
            return f"ℹ️ Пользователь {user_name} уже находится в очереди ожидания (позиция: {queue_position + 1})."
    
    elif user['status'] == 'teamed':
        # Пользователь в команде, убираем из команды и возвращаем в очередь
        team_id = user.get('team_id')
        if team_id:
            storage.remove_from_team(team_id, tg_id)
        
        storage.set_user_status(tg_id, 'waiting', None)
        storage.enqueue(tg_id)
        
        team_info = f" из команды {team_id}" if team_id else ""
        return f"✅ Пользователь {user_name} перемещен{team_info} в лист ожидания."
    
    else:
        # Неизвестный статус
        storage.set_user_status(tg_id, 'waiting', None)
        storage.enqueue(tg_id)
        return f"✅ Пользователь {user_name} перемещен в лист ожидания (был статус: {user['status']})."
