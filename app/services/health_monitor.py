"""
Система мониторинга здоровья бота и проверки состояния.
"""

import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psutil
import os
from pathlib import Path

from .logger import get_logger, bot_logger, get_metrics
from .storage import storage

logger = get_logger('health_monitor')


class HealthStatus:
    """Статус здоровья компонента."""
    
    def __init__(self, name: str, status: str, message: str = "", details: Optional[Dict[str, Any]] = None):
        self.name = name
        self.status = status  # 'healthy', 'warning', 'critical'
        self.message = message
        self.details = details or {}
        self.timestamp = time.time()


class HealthMonitor:
    """Мониторинг состояния бота."""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.checks = {}
        self.history = []
        self.max_history = 1000
        self.running = False
        self.check_interval = 60  # секунд
        self.thresholds = {
            'memory_warning': 90,    # % использования памяти (повышено для Replit)
            'memory_critical': 95,
            'cpu_warning': 85,       # % использования CPU (повышено для Replit)
            'cpu_critical': 95,
            'disk_warning': 85,      # % использования диска
            'disk_critical': 95,
            'response_warning': 2.0, # секунды
            'response_critical': 5.0,
            'error_rate_warning': 0.05,  # 5% ошибок
            'error_rate_critical': 0.15, # 15% ошибок
        }
        
    async def check_bot_connection(self) -> HealthStatus:
        """Проверяет подключение к Telegram API."""
        try:
            if not self.bot:
                return HealthStatus('bot_connection', 'critical', 'Bot instance not available')
            
            start_time = time.time()
            me = await self.bot.get_me()
            response_time = time.time() - start_time
            
            if response_time > self.thresholds['response_critical']:
                status = 'critical'
                message = f'Медленный ответ от Telegram API: {response_time:.2f}s'
            elif response_time > self.thresholds['response_warning']:
                status = 'warning'
                message = f'Замедленный ответ от Telegram API: {response_time:.2f}s'
            else:
                status = 'healthy'
                message = f'Подключение к Telegram API в порядке: @{me.username}'
            
            return HealthStatus(
                'bot_connection', 
                status, 
                message,
                {
                    'response_time': response_time,
                    'bot_username': me.username,
                    'bot_id': me.id
                }
            )
        except Exception as e:
            logger.error(f"Ошибка проверки подключения к боту: {e}")
            return HealthStatus(
                'bot_connection', 
                'critical', 
                f'Не удалось подключиться к Telegram API: {str(e)}'
            )
    
    def check_system_resources(self) -> HealthStatus:
        """Проверяет системные ресурсы."""
        try:
            # Память
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Диск
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Определяем общий статус
            if (memory_percent > self.thresholds['memory_critical'] or 
                cpu_percent > self.thresholds['cpu_critical'] or 
                disk_percent > self.thresholds['disk_critical']):
                status = 'critical'
                message = 'Критическое использование системных ресурсов'
            elif (memory_percent > self.thresholds['memory_warning'] or 
                  cpu_percent > self.thresholds['cpu_warning'] or 
                  disk_percent > self.thresholds['disk_warning']):
                status = 'warning'
                message = 'Высокое использование системных ресурсов'
            else:
                status = 'healthy'
                message = 'Системные ресурсы в норме'
            
            return HealthStatus(
                'system_resources',
                status,
                message,
                {
                    'memory_percent': memory_percent,
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk_percent,
                    'disk_free_gb': round(disk.free / (1024**3), 2),
                    'pid': os.getpid(),
                    'threads_count': threading.active_count()
                }
            )
        except Exception as e:
            logger.error(f"Ошибка проверки системных ресурсов: {e}")
            return HealthStatus(
                'system_resources',
                'warning',
                f'Не удалось проверить системные ресурсы: {str(e)}'
            )
    
    def check_storage(self) -> HealthStatus:
        """Проверяет состояние хранилища данных."""
        try:
            # Проверяем доступность файла данных
            data_file = Path('data.json')
            if not data_file.exists():
                return HealthStatus(
                    'storage',
                    'critical',
                    'Файл данных data.json не найден'
                )
            
            # Проверяем размер файла и время последней модификации
            file_stat = data_file.stat()
            file_size_mb = file_stat.st_size / (1024 * 1024)
            last_modified = datetime.fromtimestamp(file_stat.st_mtime)
            age_minutes = (datetime.now() - last_modified).total_seconds() / 60
            
            # Пытаемся загрузить данные
            try:
                data = storage.load()
                users_count = len(data.get('users', {}))
                teams_count = len(data.get('teams', {}))
                queue_count = len(data.get('queue', []))
            except Exception as e:
                return HealthStatus(
                    'storage',
                    'critical',
                    f'Не удалось загрузить данные: {str(e)}'
                )
            
            # Проверяем на предмет проблем
            if file_size_mb > 100:  # Файл больше 100MB
                status = 'warning'
                message = f'Большой размер файла данных: {file_size_mb:.1f}MB'
            elif age_minutes > 60:  # Файл не обновлялся более часа
                status = 'warning'
                message = f'Данные не обновлялись {age_minutes:.0f} минут'
            else:
                status = 'healthy'
                message = 'Хранилище данных работает нормально'
            
            return HealthStatus(
                'storage',
                status,
                message,
                {
                    'file_size_mb': round(file_size_mb, 2),
                    'last_modified': last_modified.isoformat(),
                    'age_minutes': round(age_minutes, 1),
                    'users_count': users_count,
                    'teams_count': teams_count,
                    'queue_count': queue_count
                }
            )
        except Exception as e:
            logger.error(f"Ошибка проверки хранилища: {e}")
            return HealthStatus(
                'storage',
                'warning',
                f'Ошибка при проверке хранилища: {str(e)}'
            )
    
    def check_error_rate(self) -> HealthStatus:
        """Проверяет частоту ошибок."""
        try:
            metrics = get_metrics()
            
            total_operations = metrics.get('messages_processed', 0) + metrics.get('callbacks_processed', 0)
            errors_count = metrics.get('errors_count', 0)
            
            if total_operations == 0:
                error_rate = 0
            else:
                error_rate = errors_count / total_operations
            
            if error_rate > self.thresholds['error_rate_critical']:
                status = 'critical'
                message = f'Критически высокая частота ошибок: {error_rate:.1%}'
            elif error_rate > self.thresholds['error_rate_warning']:
                status = 'warning'
                message = f'Повышенная частота ошибок: {error_rate:.1%}'
            else:
                status = 'healthy'
                message = f'Частота ошибок в норме: {error_rate:.1%}'
            
            return HealthStatus(
                'error_rate',
                status,
                message,
                {
                    'error_rate': round(error_rate, 4),
                    'errors_count': errors_count,
                    'total_operations': total_operations,
                    'last_activity': metrics.get('last_activity', 0)
                }
            )
        except Exception as e:
            logger.error(f"Ошибка проверки частоты ошибок: {e}")
            return HealthStatus(
                'error_rate',
                'warning',
                f'Не удалось проверить частоту ошибок: {str(e)}'
            )
    
    def check_logs_health(self) -> HealthStatus:
        """Проверяет состояние системы логирования."""
        try:
            logs_dir = Path('logs')
            
            if not logs_dir.exists():
                return HealthStatus(
                    'logs_health',
                    'warning',
                    'Директория логов не найдена'
                )
            
            # Проверяем размер логов
            total_size = 0
            log_files = list(logs_dir.glob('*.log*'))
            
            for log_file in log_files:
                if log_file.is_file():
                    total_size += log_file.stat().st_size
            
            total_size_mb = total_size / (1024 * 1024)
            
            # Проверяем последнюю активность в логах
            latest_log = None
            latest_time = 0
            
            for log_file in log_files:
                if log_file.is_file():
                    mtime = log_file.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_log = log_file
            
            if latest_log:
                age_minutes = (time.time() - latest_time) / 60
            else:
                age_minutes = float('inf')
            
            # Определяем статус
            if total_size_mb > 1000:  # Логи больше 1GB
                status = 'warning'
                message = f'Большой размер логов: {total_size_mb:.1f}MB'
            elif age_minutes > 10:  # Логи не обновлялись более 10 минут
                status = 'warning'
                message = f'Логи не обновлялись {age_minutes:.0f} минут'
            else:
                status = 'healthy'
                message = 'Система логирования работает нормально'
            
            return HealthStatus(
                'logs_health',
                status,
                message,
                {
                    'logs_size_mb': round(total_size_mb, 2),
                    'logs_count': len(log_files),
                    'latest_log': latest_log.name if latest_log else None,
                    'last_update_minutes': round(age_minutes, 1) if age_minutes != float('inf') else None
                }
            )
        except Exception as e:
            logger.error(f"Ошибка проверки логов: {e}")
            return HealthStatus(
                'logs_health',
                'warning',
                f'Ошибка при проверке логов: {str(e)}'
            )
    
    async def run_all_checks(self) -> Dict[str, HealthStatus]:
        """Запускает все проверки здоровья."""
        checks = {}
        
        try:
            # Асинхронные проверки
            checks['bot_connection'] = await self.check_bot_connection()
            
            # Синхронные проверки
            checks['system_resources'] = self.check_system_resources()
            checks['storage'] = self.check_storage()
            checks['error_rate'] = self.check_error_rate()
            checks['logs_health'] = self.check_logs_health()
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении проверок здоровья: {e}")
            checks['general'] = HealthStatus(
                'general',
                'critical',
                f'Критическая ошибка мониторинга: {str(e)}'
            )
        
        # Сохраняем результаты
        self.checks = checks
        
        # Добавляем в историю
        self.history.append({
            'timestamp': time.time(),
            'checks': {name: {
                'status': check.status,
                'message': check.message,
                'details': check.details
            } for name, check in checks.items()}
        })
        
        # Ограничиваем размер истории
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        return checks
    
    def get_overall_status(self) -> str:
        """Возвращает общий статус здоровья."""
        if not self.checks:
            return 'unknown'
        
        statuses = [check.status for check in self.checks.values()]
        
        if 'critical' in statuses:
            return 'critical'
        elif 'warning' in statuses:
            return 'warning'
        else:
            return 'healthy'
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Возвращает сводку о состоянии здоровья."""
        overall_status = self.get_overall_status()
        
        summary = {
            'overall_status': overall_status,
            'timestamp': time.time(),
            'checks_count': len(self.checks),
            'healthy_count': len([c for c in self.checks.values() if c.status == 'healthy']),
            'warning_count': len([c for c in self.checks.values() if c.status == 'warning']),
            'critical_count': len([c for c in self.checks.values() if c.status == 'critical']),
            'checks': {name: {
                'status': check.status,
                'message': check.message,
                'timestamp': check.timestamp
            } for name, check in self.checks.items()}
        }
        
        return summary
    
    async def start_monitoring(self):
        """Запускает непрерывный мониторинг."""
        self.running = True
        logger.info(f"🏥 Запущен мониторинг здоровья (интервал: {self.check_interval}с)")
        
        while self.running:
            try:
                await self.run_all_checks()
                
                # Логируем результаты
                summary = self.get_health_summary()
                logger.info(
                    f"🏥 Проверка здоровья: {summary['overall_status']} "
                    f"(✅{summary['healthy_count']} ⚠️{summary['warning_count']} ❌{summary['critical_count']})"
                )
                
                # Логируем критические проблемы
                for name, check in self.checks.items():
                    if check.status == 'critical':
                        logger.error(f"🚨 Критическая проблема в {name}: {check.message}")
                    elif check.status == 'warning':
                        logger.warning(f"⚠️ Предупреждение в {name}: {check.message}")
                
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    def stop_monitoring(self):
        """Останавливает мониторинг."""
        self.running = False
        logger.info("🔴 Мониторинг здоровья остановлен")


# Глобальный экземпляр монитора
health_monitor = HealthMonitor()
