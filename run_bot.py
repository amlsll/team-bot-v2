#!/usr/bin/env python3
"""
Универсальный и надежный скрипт запуска team-bot.
Автоматически предотвращает конфликты и дублирование процессов.
"""

import os
import sys
import asyncio
import logging
import argparse
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

logger = logging.getLogger('run_bot')


class SafeBotRunner:
    """Безопасный запуск бота с проверкой конфликтов."""
    
    def __init__(self):
        self.force_start = False
        self.skip_checks = False
        self.process_lock = None
    
    def check_dependencies(self) -> bool:
        """Проверка зависимостей."""
        logger.info("📦 Проверка зависимостей...")
        
        required_modules = ['aiogram', 'aiohttp', 'psutil', 'python-dotenv']
        missing_modules = []
        
        for module in required_modules:
            try:
                if module == 'python-dotenv':
                    __import__('dotenv')
                else:
                    __import__(module)
                logger.debug(f"✅ {module}: найден")
            except ImportError:
                missing_modules.append(module)
                logger.error(f"❌ {module}: не найден")
        
        if missing_modules:
            logger.error("\n💡 Для установки недостающих зависимостей выполните:")
            logger.error(f"   pip install {' '.join(missing_modules)}")
            return False
        
        logger.info("✅ Все зависимости установлены")
        return True
    
    def check_configuration(self) -> bool:
        """Проверка конфигурации."""
        logger.info("⚙️ Проверка конфигурации...")
        
        # Проверяем .env файл
        env_file = Path('.env')
        if not env_file.exists():
            logger.error("❌ Файл .env не найден")
            logger.error("💡 Создайте .env файл на основе env.sample:")
            logger.error("   cp env.sample .env")
            logger.error("   # Затем отредактируйте .env файл")
            return False
        
        # Загружаем переменные
        load_dotenv()
        
        # Проверяем обязательные переменные
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("❌ BOT_TOKEN не найден в .env файле")
            logger.error("💡 Добавьте в .env файл:")
            logger.error("   BOT_TOKEN=ваш_токен_от_BotFather")
            return False
        
        # Базовые проверки токена
        if not bot_token.count(':') == 1 or len(bot_token.split(':')[0]) < 8:
            logger.error("❌ BOT_TOKEN имеет неверный формат")
            logger.error("💡 Токен должен быть в формате: 123456789:AAA-BBB-CCC")
            return False
        
        logger.info("✅ Конфигурация корректна")
        return True
    
    async def check_existing_processes(self) -> bool:
        """Проверка уже запущенных процессов."""
        logger.info("🔍 Проверка запущенных процессов...")
        
        try:
            from app.services.process_lock import check_running_instances
            
            running_instances = check_running_instances()
            
            if running_instances:
                logger.warning(f"⚠️ Найдено {len(running_instances)} запущенных экземпляров бота:")
                for instance in running_instances:
                    logger.warning(f"   PID: {instance['pid']} | Команда: {instance['cmdline']}")
                
                if self.force_start:
                    logger.info("🔧 Принудительный запуск: останавливаем существующие процессы...")
                    from app.services.process_lock import stop_all_instances
                    stopped = stop_all_instances(force=True)
                    logger.info(f"✅ Остановлено {stopped} процессов")
                    return True
                else:
                    logger.error("\n❌ Обнаружены конфликтующие процессы!")
                    logger.error("🔧 Варианты решения:")
                    logger.error("   1. python stop_all_bots.py  # остановить все")
                    logger.error("   2. python run_bot.py --force  # принудительный запуск")
                    logger.error("   3. pkill -f 'team_bot|start_bot'  # принудительная остановка")
                    return False
            
            logger.info("✅ Конфликтующие процессы не найдены")
            return True
            
        except ImportError:
            logger.warning("⚠️ Модуль process_lock недоступен, пропускаем проверку процессов")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке процессов: {e}")
            return not self.skip_checks
    
    async def run_health_check(self) -> bool:
        """Запуск полной диагностики."""
        if self.skip_checks:
            logger.info("⏭️ Пропускаем health check по запросу")
            return True
        
        logger.info("🏥 Запуск полной диагностики...")
        
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, 'bot_health_check.py'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ Health check пройден успешно")
                return True
            else:
                logger.error("❌ Health check выявил проблемы:")
                # Выводим только важные строки из вывода
                for line in result.stdout.split('\n'):
                    if '❌' in line or 'ERROR' in line:
                        logger.error(f"   {line}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Health check превысил время ожидания")
            return True
        except FileNotFoundError:
            logger.warning("⚠️ bot_health_check.py не найден, пропускаем диагностику")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске health check: {e}")
            return not self.skip_checks
    
    async def start_bot(self) -> bool:
        """Запуск бота."""
        logger.info("🚀 Запуск team-bot...")
        
        try:
            # Используем существующий надежный стартер
            from start_bot import main as start_main
            
            result = await start_main()
            return result == 0
            
        except ImportError:
            logger.error("❌ Не удалось импортировать start_bot")
            logger.error("💡 Убедитесь, что файл start_bot.py существует")
            return False
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при запуске: {e}")
            return False
    
    async def run(self, force: bool = False, skip_checks: bool = False) -> bool:
        """Главный метод запуска."""
        self.force_start = force
        self.skip_checks = skip_checks
        
        logger.info("=" * 60)
        logger.info("🤖 TEAM-BOT SAFE RUNNER")
        logger.info("=" * 60)
        
        # Этап 1: Базовые проверки
        if not self.check_dependencies():
            return False
        
        if not self.check_configuration():
            return False
        
        # Этап 2: Проверка процессов
        if not await self.check_existing_processes():
            return False
        
        # Этап 3: Health check
        if not await self.run_health_check():
            logger.warning("⚠️ Health check не пройден, но продолжаем запуск...")
        
        # Этап 4: Запуск бота
        logger.info("🎯 Все проверки пройдены, запускаем бота...")
        return await self.start_bot()


def main():
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Безопасный запуск team-bot с автоматическими проверками"
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Принудительный запуск с остановкой конфликтующих процессов'
    )
    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='Пропустить health check (не рекомендуется)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Включить отладочный вывод'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        runner = SafeBotRunner()
        success = asyncio.run(runner.run(
            force=args.force,
            skip_checks=args.skip_checks
        ))
        
        logger.info("=" * 60)
        if success:
            logger.info("✅ TEAM-BOT ЗАВЕРШИЛ РАБОТУ КОРРЕКТНО")
        else:
            logger.error("❌ TEAM-BOT ЗАВЕРШИЛ РАБОТУ С ОШИБКАМИ")
        logger.info("=" * 60)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("\n⌨️ Получено прерывание с клавиатуры")
        return 0
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
        sys.exit(0)
