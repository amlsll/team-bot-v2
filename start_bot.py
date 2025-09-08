#!/usr/bin/env python3
"""
Надёжный скрипт запуска бота с автоматической диагностикой и восстановлением.
Этот скрипт обеспечивает максимальную стабильность работы.
"""

import asyncio
import logging
import sys
import os
import signal
import time
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_startup.log', encoding='utf-8')
    ]
)

logger = logging.getLogger('bot_startup')

class BotStarter:
    """Класс для надежного запуска бота."""
    
    def __init__(self):
        self.max_retries = 5
        self.retry_delay = 5
        self.bot = None
        self.dp = None
        self.should_stop = False
        self.process_lock = None
        
    async def acquire_process_lock(self):
        """Получение блокировки процесса."""
        try:
            from app.services.process_lock import ProcessLock
            
            self.process_lock = ProcessLock("team_bot")
            
            # Проверяем запущенные экземпляры перед блокировкой
            running_instances = self.process_lock.get_running_instances()
            if running_instances:
                logger.error("\n❌ Обнаружены уже запущенные экземпляры бота:")
                for instance in running_instances:
                    logger.error(f"   PID: {instance['pid']} | Команда: {instance['cmdline']}")
                
                logger.error("\n🔧 Для остановки всех экземпляров выполните:")
                logger.error("   python stop_all_bots.py")
                logger.error("   или: pkill -f 'team_bot|start_bot|python.*app'")
                return False
            
            # Получаем блокировку
            if not self.process_lock.acquire(timeout=10):
                logger.error("❌ Не удалось получить блокировку процесса")
                return False
            
            logger.info("✅ Блокировка процесса получена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении блокировки: {e}")
            return False

    async def pre_start_checks(self):
        """Выполнение проверок перед запуском."""
        logger.info("🔍 Выполнение предварительных проверок...")
        
        # Запускаем диагностику
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, 'bot_health_check.py'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ Диагностика пройдена успешно")
                return True
            else:
                logger.error(f"❌ Диагностика обнаружила проблемы:\n{result.stdout}\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Диагностика превысила время ожидания, продолжаем запуск")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Не удалось запустить диагностику: {e}, продолжаем запуск")
            return True
    
    async def init_bot(self):
        """Инициализация бота и диспетчера."""
        try:
            from app.bot import bot, dp
            self.bot = bot
            self.dp = dp
            
            # Проверяем подключение
            me = await self.bot.get_me()
            logger.info(f"✅ Бот инициализирован: @{me.username}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            return False
    
    async def cleanup_webhook(self):
        """Очистка webhook для polling режима."""
        try:
            webhook_info = await self.bot.get_webhook_info()
            if webhook_info.url:
                logger.info(f"🧹 Очищаем webhook: {webhook_info.url}")
                await self.bot.delete_webhook(drop_pending_updates=True)
                logger.info("✅ Webhook очищен")
            else:
                logger.info("ℹ️ Webhook не установлен")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при очистке webhook: {e}")
    
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов."""
        def signal_handler(signum, frame):
            logger.info(f"📡 Получен сигнал {signum}, инициируем остановку...")
            self.should_stop = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    async def start_polling_with_retry(self):
        """Запуск polling с автоматической перезагрузкой."""
        retry_count = 0
        
        while retry_count < self.max_retries and not self.should_stop:
            try:
                logger.info(f"🚀 Запуск polling (попытка {retry_count + 1}/{self.max_retries})")
                
                # Очищаем webhook перед каждой попыткой
                await self.cleanup_webhook()
                
                # Запускаем polling
                await self.dp.start_polling(
                    self.bot,
                    handle_signals=False,
                    fast=True,
                    allowed_updates=['message', 'callback_query']
                )
                
                # Если дошли сюда, значит polling остановился корректно
                logger.info("📴 Polling остановлен корректно")
                break
                
            except Exception as e:
                retry_count += 1
                logger.error(f"❌ Ошибка polling (попытка {retry_count}): {e}")
                
                if retry_count < self.max_retries:
                    logger.info(f"⏳ Ожидание {self.retry_delay} сек перед повтором...")
                    await asyncio.sleep(self.retry_delay)
                    
                    # Увеличиваем задержку для следующей попытки
                    self.retry_delay = min(self.retry_delay * 2, 60)
                else:
                    logger.error("💥 Превышено максимальное количество попыток")
                    raise
    
    async def graceful_shutdown(self):
        """Корректное завершение работы."""
        logger.info("🛑 Начинаем корректную остановку...")
        
        try:
            if self.bot:
                await self.bot.session.close()
                logger.info("✅ Сессия бота закрыта")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии сессии: {e}")
        
        # Освобождаем блокировку процесса
        try:
            if self.process_lock:
                self.process_lock.release()
                logger.info("✅ Блокировка процесса освобождена")
        except Exception as e:
            logger.error(f"❌ Ошибка при освобождении блокировки: {e}")
        
        logger.info("✅ Бот остановлен корректно")
    
    async def run(self):
        """Главный метод запуска."""
        try:
            # Настройка обработчиков сигналов
            self.setup_signal_handlers()
            
            # Получение блокировки процесса (первым делом)
            if not await self.acquire_process_lock():
                logger.error("💥 Не удалось получить блокировку процесса")
                return False
            
            # Предварительные проверки
            if not await self.pre_start_checks():
                logger.error("💥 Предварительные проверки не пройдены")
                return False
            
            # Инициализация бота
            if not await self.init_bot():
                logger.error("💥 Не удалось инициализировать бота")
                return False
            
            # Запуск с автоматическими повторами
            await self.start_polling_with_retry()
            
            return True
            
        except KeyboardInterrupt:
            logger.info("⌨️ Получено прерывание с клавиатуры")
        except Exception as e:
            logger.error(f"💥 Критическая ошибка: {e}")
            return False
        finally:
            await self.graceful_shutdown()
        
        return True

async def main():
    """Точка входа."""
    # Загружаем переменные окружения
    load_dotenv()
    
    logger.info("=" * 60)
    logger.info("🤖 ЗАПУСК TEAM-BOT")
    logger.info("=" * 60)
    
    # Проверяем наличие токена
    if not os.getenv('BOT_TOKEN'):
        logger.error("❌ BOT_TOKEN не найден в переменных окружения")
        logger.error("Создайте файл .env на основе env.sample")
        return 1
    
    # Создаем и запускаем starter
    starter = BotStarter()
    success = await starter.run()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ TEAM-BOT ЗАВЕРШИЛ РАБОТУ КОРРЕКТНО")
    else:
        logger.error("❌ TEAM-BOT ЗАВЕРШИЛ РАБОТУ С ОШИБКАМИ")
    logger.info("=" * 60)
    
    return 0 if success else 1

if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
        sys.exit(0)
