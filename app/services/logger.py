"""
Централизованная система логирования и мониторинга для бота.
"""

import logging
import logging.handlers
import os
import json
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import threading
import time
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """Форматтер для JSON логов."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Добавляем дополнительные поля если есть
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'chat_id'):
            log_data['chat_id'] = record.chat_id
        if hasattr(record, 'handler_name'):
            log_data['handler_name'] = record.handler_name
        if hasattr(record, 'duration'):
            log_data['duration_ms'] = record.duration
        if hasattr(record, 'error_type'):
            log_data['error_type'] = record.error_type
        if hasattr(record, 'stack_trace'):
            log_data['stack_trace'] = record.stack_trace
            
        # Добавляем exception info если есть
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_data, ensure_ascii=False)


class BotLogger:
    """Менеджер логирования для бота."""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Счетчики для метрик
        self._metrics = {
            'messages_processed': 0,
            'callbacks_processed': 0,
            'errors_count': 0,
            'users_active': set(),
            'handlers_timing': {},
            'last_activity': time.time()
        }
        self._metrics_lock = threading.Lock()
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Настраивает все логгеры."""
        
        # Создаем основной логгер
        self.main_logger = logging.getLogger('team_bot')
        self.main_logger.setLevel(logging.DEBUG)
        
        # Очищаем существующие handlers
        self.main_logger.handlers.clear()
        
        # Console handler с цветным выводом
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.main_logger.addHandler(console_handler)
        
        # File handler для всех логов
        all_logs_file = self.logs_dir / "bot_all.log"
        file_handler = logging.handlers.TimedRotatingFileHandler(
            all_logs_file,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(console_formatter)
        self.main_logger.addHandler(file_handler)
        
        # JSON handler для структурированных логов
        json_logs_file = self.logs_dir / "bot_structured.jsonl"
        json_handler = logging.handlers.TimedRotatingFileHandler(
            json_logs_file,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.INFO)
        json_handler.setFormatter(JsonFormatter())
        self.main_logger.addHandler(json_handler)
        
        # Error handler для ошибок
        error_logs_file = self.logs_dir / "bot_errors.log"
        error_handler = logging.handlers.TimedRotatingFileHandler(
            error_logs_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JsonFormatter())
        self.main_logger.addHandler(error_handler)
        
        # Performance handler для метрик производительности
        perf_logs_file = self.logs_dir / "bot_performance.jsonl"
        self.perf_handler = logging.handlers.TimedRotatingFileHandler(
            perf_logs_file,
            when='H',  # H для hourly, вместо 'hourly'
            interval=1,
            backupCount=24,
            encoding='utf-8'
        )
        self.perf_handler.setFormatter(JsonFormatter())
        
        # Создаем отдельный логгер для метрик
        self.metrics_logger = logging.getLogger('team_bot.metrics')
        self.metrics_logger.setLevel(logging.INFO)
        self.metrics_logger.addHandler(self.perf_handler)
        self.metrics_logger.propagate = False
        
        # Настраиваем уровень логирования aiogram
        logging.getLogger('aiogram').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        
        self.main_logger.info("🔧 Система логирования инициализирована")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Возвращает логгер с указанным именем."""
        return logging.getLogger(f'team_bot.{name}')
    
    def log_message_processed(self, user_id: int, chat_id: int, message_text: str, handler_name: str = None):
        """Логирует обработку сообщения."""
        with self._metrics_lock:
            self._metrics['messages_processed'] += 1
            self._metrics['users_active'].add(user_id)
            self._metrics['last_activity'] = time.time()
        
        logger = self.get_logger('messages')
        logger.info(
            f"📩 Сообщение обработано: {message_text[:50]}{'...' if len(message_text) > 50 else ''}",
            extra={
                'user_id': user_id,
                'chat_id': chat_id,
                'handler_name': handler_name,
                'message_length': len(message_text)
            }
        )
    
    def log_callback_processed(self, user_id: int, chat_id: int, callback_data: str, handler_name: str = None):
        """Логирует обработку callback."""
        with self._metrics_lock:
            self._metrics['callbacks_processed'] += 1
            self._metrics['users_active'].add(user_id)
            self._metrics['last_activity'] = time.time()
        
        logger = self.get_logger('callbacks')
        logger.info(
            f"🔘 Callback обработан: {callback_data}",
            extra={
                'user_id': user_id,
                'chat_id': chat_id,
                'handler_name': handler_name,
                'callback_data': callback_data
            }
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None, user_id: int = None):
        """Логирует ошибку с контекстом."""
        with self._metrics_lock:
            self._metrics['errors_count'] += 1
        
        logger = self.get_logger('errors')
        
        extra_data = {
            'error_type': type(error).__name__,
            'stack_trace': traceback.format_exc()
        }
        
        if user_id:
            extra_data['user_id'] = user_id
        if context:
            extra_data.update(context)
        
        logger.error(
            f"❌ Ошибка: {str(error)}",
            extra=extra_data,
            exc_info=True
        )
    
    def log_handler_timing(self, handler_name: str, duration_ms: float, user_id: int = None):
        """Логирует время выполнения обработчика."""
        with self._metrics_lock:
            if handler_name not in self._metrics['handlers_timing']:
                self._metrics['handlers_timing'][handler_name] = []
            self._metrics['handlers_timing'][handler_name].append(duration_ms)
            
            # Оставляем только последние 100 измерений
            if len(self._metrics['handlers_timing'][handler_name]) > 100:
                self._metrics['handlers_timing'][handler_name] = \
                    self._metrics['handlers_timing'][handler_name][-100:]
        
        if duration_ms > 1000:  # Логируем только медленные операции
            logger = self.get_logger('performance')
            logger.warning(
                f"⏱️ Медленный обработчик: {handler_name} ({duration_ms:.2f}ms)",
                extra={
                    'handler_name': handler_name,
                    'duration': duration_ms,
                    'user_id': user_id
                }
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает текущие метрики."""
        with self._metrics_lock:
            # Вычисляем средние времена выполнения
            avg_timings = {}
            for handler, timings in self._metrics['handlers_timing'].items():
                if timings:
                    avg_timings[handler] = {
                        'avg_ms': sum(timings) / len(timings),
                        'max_ms': max(timings),
                        'min_ms': min(timings),
                        'count': len(timings)
                    }
            
            return {
                'messages_processed': self._metrics['messages_processed'],
                'callbacks_processed': self._metrics['callbacks_processed'],
                'errors_count': self._metrics['errors_count'],
                'active_users_count': len(self._metrics['users_active']),
                'last_activity': self._metrics['last_activity'],
                'handlers_performance': avg_timings,
                'uptime_seconds': time.time() - self._start_time if hasattr(self, '_start_time') else 0
            }
    
    def log_metrics(self):
        """Записывает текущие метрики в лог."""
        metrics = self.get_metrics()
        self.metrics_logger.info("📊 Метрики производительности", extra=metrics)
    
    def reset_metrics(self):
        """Сбрасывает счетчики метрик."""
        with self._metrics_lock:
            self._metrics['users_active'].clear()
            self._metrics['handlers_timing'].clear()
    
    def start_metrics_logging(self, interval: int = 300):  # каждые 5 минут
        """Запускает периодическое логирование метрик."""
        self._start_time = time.time()
        
        def log_metrics_periodically():
            while True:
                time.sleep(interval)
                self.log_metrics()
        
        thread = threading.Thread(target=log_metrics_periodically, daemon=True)
        thread.start()
        
        self.main_logger.info(f"📊 Запущено периодическое логирование метрик (каждые {interval}с)")


# Глобальный экземпляр логгера
bot_logger = BotLogger()

# Удобные функции для использования в других модулях
def get_logger(name: str) -> logging.Logger:
    """Возвращает логгер для указанного модуля."""
    return bot_logger.get_logger(name)

def log_message(user_id: int, chat_id: int, message_text: str, handler_name: str = None):
    """Логирует обработку сообщения."""
    bot_logger.log_message_processed(user_id, chat_id, message_text, handler_name)

def log_callback(user_id: int, chat_id: int, callback_data: str, handler_name: str = None):
    """Логирует обработку callback."""
    bot_logger.log_callback_processed(user_id, chat_id, callback_data, handler_name)

def log_error(error: Exception, context: Dict[str, Any] = None, user_id: int = None):
    """Логирует ошибку."""
    bot_logger.log_error(error, context, user_id)

def log_timing(handler_name: str, duration_ms: float, user_id: int = None):
    """Логирует время выполнения."""
    bot_logger.log_handler_timing(handler_name, duration_ms, user_id)

def get_metrics() -> Dict[str, Any]:
    """Возвращает метрики."""
    return bot_logger.get_metrics()
