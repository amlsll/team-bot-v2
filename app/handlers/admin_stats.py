"""
Админская команда /adm_stats для получения статистики.
"""

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..services.acl import require_admin
from ..services.storage import Storage

router = Router()


async def get_stats_response():
    """Получает текст статистики для отображения."""
    storage = Storage()
    
    # Получаем основную статистику
    queue_size = storage.get_queue_size()
    active_teams_count = storage.get_active_teams_count()
    avg_team_size = storage.get_active_teams_avg_size()
    
    # Получаем первые 10 username в очереди
    queue_usernames = storage.get_queue_usernames(limit=10)
    
    # Формируем ответ
    response = "📊 **Статистика бота**\n\n"
    response += f"⏳ **Ожидающих в очереди:** {queue_size}\n"
    response += f"🏆 **Активных команд:** {active_teams_count}\n"
    response += f"📈 **Средний размер команды:** {avg_team_size:.1f}\n\n"
    
    if queue_usernames:
        response += "👥 **Первые в очереди:**\n"
        for i, username in enumerate(queue_usernames, 1):
            response += f"{i}. {username}\n"
    else:
        response += "👥 **Очередь пуста**\n"
    
    return response

@router.message(Command("adm_stats"))
@require_admin
async def cmd_adm_stats(message: Message):
    """Админская команда для получения сводной статистики."""
    response = await get_stats_response()
    await message.reply(response)
