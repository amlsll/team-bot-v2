"""
Админская команда /adm_match для комплектования команд.
"""

import os
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..services.acl import require_admin
from ..services.storage import Storage
from ..services.matcher import match_round
from ..services.notify import NotificationService

router = Router()


@router.message(Command("adm_match"))
@require_admin
async def cmd_adm_match(message: Message):
    """Админская команда для проведения одного раунда комплектования."""
    storage = Storage()
    notify_service = NotificationService(message.bot)
    
    # Получаем настройки из env
    team_base = int(os.getenv('TEAM_BASE', '5'))
    elastic_max = int(os.getenv('ELASTIC_MAX', '2'))
    
    # Загружаем текущее состояние
    store = storage.load()
    queue = store['queue'].copy()
    
    if len(queue) < team_base:
        await message.reply(f"Недостаточно людей в очереди для комплектования. Нужно минимум {team_base}, а в очереди {len(queue)}.")
        return
    
    # Выполняем матчинг
    teams_data, remaining_queue = match_round(queue, team_base, elastic_max)
    
    if not teams_data:
        await message.reply("Не удалось сформировать ни одной команды.")
        return
    
    # Создаем команды и обновляем пользователей
    created_teams = []
    for team_members in teams_data:
        # Создаем команду в storage
        team_id = storage.create_team(team_members)
        
        # Обновляем статус участников
        for tg_id in team_members:
            storage.set_user_status(tg_id, 'teamed', team_id)
        
        # Убираем участников из очереди
        for tg_id in team_members:
            storage.remove_from_queue(tg_id)
        
        created_teams.append(team_id)
    
    # Обновляем очередь (остаток)
    store = storage.load()
    store['queue'] = remaining_queue
    storage.save(store)
    
    # Отправляем карточки командам
    for team_id in created_teams:
        team = storage.get_team(team_id)
        if team:
            await notify_service.send_team_card_to_members(team)
    
    # Отвечаем админу
    teams_count = len(created_teams)
    remaining_count = len(remaining_queue)
    
    response = f"✅ Сформировано команд: {teams_count}\n"
    response += f"📋 Команды: {', '.join(created_teams)}\n"
    response += f"⏳ В очереди осталось: {remaining_count}"
    
    await message.reply(response)
