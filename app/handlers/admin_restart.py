"""
Обработчик команды перезапуска бота.
"""

import os
import sys
import signal
import asyncio
import logging
from datetime import datetime
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..services.acl import require_admin

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("adm_restart"))
@require_admin
async def cmd_restart_bot(message: Message):
    """Админская команда для перезапуска бота."""
    try:
        # Отправляем подтверждение
        await message.reply("🔄 Перезапускаю бота...")
        
        # Небольшая задержка для отправки сообщения
        await asyncio.sleep(1)
        
        logger.info(f"Перезапуск инициирован админом {message.from_user.id}")
        
        # Создаем флаг перезапуска
        restart_flag = os.path.join(os.path.dirname(__file__), '../../.restart_required')
        with open(restart_flag, 'w') as f:
            f.write(f"Restart initiated by admin {message.from_user.id} at {datetime.now().isoformat()}")
        
        # Отправляем сигнал завершения процесса
        # Внешний скрипт должен отслеживать этот сигнал и перезапускать бота
        os.kill(os.getpid(), signal.SIGTERM)
        
    except Exception as e:
        logger.error(f"Ошибка при перезапуске: {e}")
        await message.reply(f"❌ Ошибка при перезапуске: {e}")


@router.message(Command("adm_shutdown"))
@require_admin
async def cmd_shutdown_bot(message: Message):
    """Админская команда для остановки бота."""
    try:
        # Отправляем подтверждение
        await message.reply("🛑 Останавливаю бота...")
        
        # Небольшая задержка для отправки сообщения  
        await asyncio.sleep(1)
        
        logger.info(f"Остановка инициирована админом {message.from_user.id}")
        
        # Создаем флаг остановки
        shutdown_flag = os.path.join(os.path.dirname(__file__), '../../.shutdown_required')
        with open(shutdown_flag, 'w') as f:
            f.write(f"Shutdown initiated by admin {message.from_user.id} at {datetime.now().isoformat()}")
        
        # Отправляем сигнал завершения
        os.kill(os.getpid(), signal.SIGTERM)
        
    except Exception as e:
        logger.error(f"Ошибка при остановке: {e}")
        await message.reply(f"❌ Ошибка при остановке: {e}")


@router.message(Command("adm_status"))
@require_admin
async def cmd_bot_status(message: Message):
    """Показывает детальный статус бота."""
    try:
        import psutil
        import platform
        from datetime import datetime
        
        # Информация о процессе
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Время запуска процесса
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time
        
        # Информация о системе
        cpu_percent = process.cpu_percent()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        # Проверяем флаги
        restart_flag = os.path.join(os.path.dirname(__file__), '../../.restart_required')
        shutdown_flag = os.path.join(os.path.dirname(__file__), '../../.shutdown_required')
        
        restart_pending = os.path.exists(restart_flag)
        shutdown_pending = os.path.exists(shutdown_flag)
        
        response = f"""📊 **Статус бота**

🤖 **Процесс:**
• PID: {os.getpid()}
• Время запуска: {create_time.strftime('%Y-%m-%d %H:%M:%S')}
• Uptime: {str(uptime).split('.')[0]}
• CPU: {cpu_percent:.1f}%
• RAM: {memory_mb:.1f} MB

🖥️ **Система:**
• Платформа: {platform.system()} {platform.release()}
• Python: {platform.python_version()}
• Архитектура: {platform.machine()}

🔧 **Состояние:**
{"⚠️ Ожидает перезапуска" if restart_pending else ""}
{"🛑 Ожидает остановки" if shutdown_pending else ""}
{"✅ Работает нормально" if not restart_pending and not shutdown_pending else ""}

🎛️ **Команды:**
• `/adm_restart` — перезапуск
• `/adm_shutdown` — остановка
• `/adm_update_check` — проверить обновления"""
        
        await message.reply(response)
        
    except ImportError:
        # Если psutil не установлен
        response = f"""📊 **Базовый статус бота**

🤖 **Процесс:** PID {os.getpid()}
⚠️ Для детального мониторинга установите: `pip install psutil`

🎛️ **Команды:**
• `/adm_restart` — перезапуск
• `/adm_shutdown` — остановка"""
        
        await message.reply(response)
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        await message.reply(f"❌ Ошибка: {e}")
