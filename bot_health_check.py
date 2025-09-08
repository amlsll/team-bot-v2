#!/usr/bin/env python3
"""
Скрипт для проверки состояния бота и диагностики проблем.
Запускать этот скрипт перед стартом бота для выявления потенциальных проблем.
"""

import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_telegram_connection():
    """Проверка подключения к Telegram API."""
    try:
        from aiogram import Bot
        
        token = os.getenv('BOT_TOKEN')
        if not token:
            logger.error("❌ BOT_TOKEN не найден в переменных окружения")
            return False
        
        bot = Bot(token=token)
        
        try:
            me = await bot.get_me()
            logger.info(f"✅ Подключение к Telegram API успешно: @{me.username} ({me.first_name})")
            
            # Проверяем webhook
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                logger.warning(f"⚠️ Активен webhook: {webhook_info.url}")
                logger.info("Для polling режима webhook будет автоматически удален")
            else:
                logger.info("✅ Webhook не установлен")
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Telegram API: {e}")
            return False
        finally:
            await bot.session.close()
            
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта aiogram: {e}")
        return False

def check_environment():
    """Проверка переменных окружения."""
    logger.info("🔍 Проверка переменных окружения...")
    
    required_vars = ['BOT_TOKEN']
    optional_vars = ['ADMIN_CODE', 'TEAM_BASE', 'ELASTIC_MAX', 'USE_WEBHOOK', 'WEBHOOK_URL', 'PORT']
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var}: установлен")
        else:
            logger.error(f"❌ {var}: не установлен (обязательный)")
            all_good = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var}: {value}")
        else:
            logger.info(f"ℹ️ {var}: не установлен (опциональный)")
    
    return all_good

def check_file_permissions():
    """Проверка прав доступа к файлам."""
    logger.info("📁 Проверка файловой системы...")
    
    files_to_check = [
        'data.json',
        'bot.log'
    ]
    
    all_good = True
    
    for filename in files_to_check:
        filepath = Path(filename)
        
        if filepath.exists():
            if filepath.is_file() and os.access(filepath, os.R_OK | os.W_OK):
                logger.info(f"✅ {filename}: доступен для чтения/записи")
            else:
                logger.error(f"❌ {filename}: нет прав доступа")
                all_good = False
        else:
            # Проверяем, можем ли создать файл
            try:
                filepath.touch()
                filepath.unlink()
                logger.info(f"✅ {filename}: можно создать")
            except Exception as e:
                logger.error(f"❌ {filename}: невозможно создать - {e}")
                all_good = False
    
    return all_good

def check_imports():
    """Проверка импортов модулей."""
    logger.info("📦 Проверка импортов...")
    
    modules_to_check = [
        'aiogram',
        'aiohttp',
        'dotenv'
    ]
    
    all_good = True
    
    for module in modules_to_check:
        try:
            __import__(module)
            logger.info(f"✅ {module}: импортирован успешно")
        except ImportError as e:
            logger.error(f"❌ {module}: ошибка импорта - {e}")
            all_good = False
    
    return all_good

def check_running_processes():
    """Проверка уже запущенных экземпляров бота."""
    logger.info("🔍 Проверка запущенных процессов...")
    
    try:
        from app.services.process_lock import check_running_instances
        
        running_instances = check_running_instances()
        
        if running_instances:
            logger.warning(f"⚠️ Найдено {len(running_instances)} запущенных экземпляров бота:")
            for instance in running_instances:
                logger.warning(f"   PID: {instance['pid']} | Команда: {instance['cmdline']}")
            
            logger.warning("\n🔧 Для остановки всех экземпляров выполните:")
            logger.warning("   python stop_all_bots.py")
            logger.warning("   или: pkill -f 'team_bot|start_bot|python.*app'")
            
            return False
        else:
            logger.info("✅ Запущенные экземпляры бота не найдены")
            return True
            
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта process_lock: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке процессов: {e}")
        return False

def check_app_structure():
    """Проверка структуры приложения."""
    logger.info("🏗️ Проверка структуры приложения...")
    
    required_files = [
        'app/__init__.py',
        'app/bot.py',
        'app/__main__.py',
        'app/handlers/user_start.py',
        'app/services/storage.py',
        'app/services/process_lock.py'
    ]
    
    all_good = True
    
    for filepath in required_files:
        if Path(filepath).exists():
            logger.info(f"✅ {filepath}: существует")
        else:
            logger.error(f"❌ {filepath}: не найден")
            all_good = False
    
    return all_good

async def test_start_handler():
    """Тестирование обработчика /start."""
    logger.info("🧪 Тестирование обработчика /start...")
    
    try:
        # Импортируем без запуска бота
        from app.handlers.user_start import cmd_start, router
        logger.info("✅ Обработчик /start импортирован успешно")
        
        # Проверяем что роутер зарегистрирован
        handlers = getattr(router, '_handlers', [])
        logger.info(f"✅ Найдено {len(handlers)} обработчиков в роутере")
        
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании /start: {e}")
        return False

async def main():
    """Главная функция диагностики."""
    logger.info("🔧 Начинаем диагностику бота...")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    checks = [
        ("Переменные окружения", check_environment),
        ("Импорты модулей", check_imports),
        ("Структура приложения", check_app_structure),
        ("Файловая система", check_file_permissions),
        ("Запущенные процессы", check_running_processes),
        ("Подключение к Telegram", check_telegram_connection),
        ("Обработчик /start", test_start_handler),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} ---")
        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()
            
            if not result:
                all_passed = False
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке '{check_name}': {e}")
            all_passed = False
    
    logger.info("\n" + "="*50)
    if all_passed:
        logger.info("🎉 Все проверки пройдены! Бот готов к запуску.")
        return 0
    else:
        logger.error("💥 Обнаружены проблемы. Исправьте их перед запуском бота.")
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
