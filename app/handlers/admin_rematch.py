"""
Админская команда /adm_rematch для расформирования команд.
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..services.acl import require_admin
from ..services.storage import Storage

router = Router()


@router.message(Command("adm_rematch"))
@require_admin
async def cmd_adm_rematch(message: Message):
    """Админская команда для расформирования команды."""
    # Парсим аргументы команды
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Использование: /adm_rematch <team_id> [--front]")
        return
    
    team_id = args[1]
    add_to_front = "--front" in args
    
    storage = Storage()
    
    # Получаем команду
    team = storage.get_team(team_id)
    if not team:
        await message.reply(f"Команда {team_id} не найдена.")
        return
    
    if team['status'] != 'active':
        await message.reply(f"Команда {team_id} уже неактивна.")
        return
    
    # Получаем участников команды
    members = team['members'].copy()
    
    # Расформировываем команду
    store = storage.load()
    
    # Архивируем команду
    team['status'] = 'archived'
    
    # Обновляем статус участников
    for tg_id in members:
        storage.set_user_status(tg_id, 'waiting', None)
    
    # Добавляем участников в очередь
    if add_to_front:
        # Добавляем в начало очереди (в обратном порядке, чтобы сохранить порядок)
        for tg_id in reversed(members):
            if tg_id not in store['queue']:
                store['queue'].insert(0, tg_id)
    else:
        # Добавляем в конец очереди
        for tg_id in members:
            if tg_id not in store['queue']:
                store['queue'].append(tg_id)
    
    # Сохраняем изменения
    storage.save(store)
    
    # Формируем ответ
    position_text = "в начало" if add_to_front else "в конец"
    response = f"✅ Команда {team_id} расформирована.\n"
    response += f"👥 Участники ({len(members)}) добавлены {position_text} очереди."
    
    await message.reply(response)
