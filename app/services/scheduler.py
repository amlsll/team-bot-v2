"""
Планировщик для автоматического объединения команд.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from .storage import Storage
from .matcher import match_round
from .notify import NotificationService

logger = logging.getLogger(__name__)


class MatchScheduler:
    """Планировщик автоматического объединения команд каждые 2 дня в 12:00."""
    
    def __init__(self, bot):
        self.bot = bot
        self.storage = Storage()
        self.notify_service = NotificationService(bot)
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    def start(self):
        """Запускает планировщик."""
        if self._running:
            logger.warning("Планировщик уже запущен")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Планировщик автоматического объединения команд запущен")
    
    def stop(self):
        """Останавливает планировщик."""
        if not self._running:
            return
        
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        
        logger.info("Планировщик автоматического объединения команд остановлен")
    
    def get_next_match_time(self) -> datetime:
        """Возвращает время следующего объединения команд."""
        now = datetime.now()
        
        # Начинаем с сегодняшнего дня в 12:00
        next_match = now.replace(hour=12, minute=0, second=0, microsecond=0)
        
        # Если уже прошло 12:00 сегодня, берем завтра
        if now.hour >= 12:
            next_match += timedelta(days=1)
        
        # Корректируем до ближайшего "каждые 2 дня"
        # Используем 1 января 2024 как опорную точку
        epoch_date = datetime(2024, 1, 1)
        days_since_epoch = (next_match.date() - epoch_date.date()).days
        
        # Если количество дней не кратно 2, добавляем день
        if days_since_epoch % 2 != 0:
            next_match += timedelta(days=1)
        
        return next_match
    
    def get_next_match_time_str(self) -> str:
        """Возвращает строковое представление времени следующего объединения."""
        next_time = self.get_next_match_time()
        return next_time.strftime("%d %B в %H:%M")
    
    async def _scheduler_loop(self):
        """Основной цикл планировщика."""
        try:
            while self._running:
                # Вычисляем время до следующего объединения
                next_match_time = self.get_next_match_time()
                now = datetime.now()
                sleep_seconds = (next_match_time - now).total_seconds()
                
                logger.info(f"Следующее автоматическое объединение запланировано на: {next_match_time}")
                
                # Ждем до нужного времени
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)
                
                # Проверяем, что еще работаем
                if not self._running:
                    break
                
                # Выполняем объединение команд
                await self._perform_auto_match()
                
                # Ждем минуту, чтобы избежать повторного срабатывания в ту же минуту
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("Планировщик был отменен")
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}", exc_info=True)
    
    async def _perform_auto_match(self):
        """Выполняет автоматическое объединение команд."""
        try:
            import os
            
            # Получаем настройки
            team_base = int(os.getenv('TEAM_BASE', '5'))
            elastic_max = int(os.getenv('ELASTIC_MAX', '2'))
            
            # Загружаем текущее состояние
            store = self.storage.load()
            queue = store['queue'].copy()
            
            if len(queue) < team_base:
                logger.info(f"Недостаточно людей в очереди для автоматического объединения. Нужно минимум {team_base}, а в очереди {len(queue)}.")
                return
            
            # Выполняем матчинг
            teams_data, remaining_queue = match_round(queue, team_base, elastic_max)
            
            if not teams_data:
                logger.info("Автоматическое объединение: не удалось сформировать ни одной команды.")
                return
            
            # Создаем команды и обновляем пользователей
            created_teams = []
            for team_members in teams_data:
                # Создаем команду в storage
                team_id = self.storage.create_team(team_members)
                
                # Обновляем статус участников
                for tg_id in team_members:
                    self.storage.set_user_status(tg_id, 'teamed', team_id)
                
                # Убираем участников из очереди
                for tg_id in team_members:
                    self.storage.remove_from_queue(tg_id)
                
                created_teams.append(team_id)
            
            # Обновляем очередь (остаток)
            store = self.storage.load()
            store['queue'] = remaining_queue
            self.storage.save(store)
            
            # Отправляем карточки командам
            for team_id in created_teams:
                team = self.storage.get_team(team_id)
                if team:
                    await self.notify_service.send_team_card_to_members(team)
            
            teams_count = len(created_teams)
            remaining_count = len(remaining_queue)
            
            logger.info(f"Автоматическое объединение завершено: создано команд {teams_count}, в очереди осталось {remaining_count}")
            
            # Уведомляем админов о результатах (если настроен MOD_CHAT_ID)
            mod_chat_id = os.getenv('MOD_CHAT_ID')
            if mod_chat_id:
                admin_message = f"""🤖 Автоматическое объединение команд завершено

✅ Сформировано команд: {teams_count}
📋 Команды: {', '.join(created_teams)}
⏳ В очереди осталось: {remaining_count}"""
                
                await self.notify_service.send_to_moderators(admin_message)
                
        except Exception as e:
            logger.error(f"Ошибка при автоматическом объединении команд: {e}", exc_info=True)
