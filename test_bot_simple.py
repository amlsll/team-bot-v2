#!/usr/bin/env python3
"""
Простой тест бота для проверки базовой функциональности.
Используйте этот скрипт для быстрой проверки работы бота.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_basic_bot():
    """Простой тест основных функций бота."""
    print("🧪 ПРОСТОЙ ТЕСТ TEAM-BOT")
    print("=" * 40)
    
    # Проверка токена
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN не найден")
        print("💡 Добавьте BOT_TOKEN в переменные окружения или Secrets")
        return False
    
    try:
        # Импортируем aiogram
        from aiogram import Bot
        
        # Создаем бота
        bot = Bot(token=bot_token)
        
        print("🔄 Тест подключения к Telegram API...")
        
        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"✅ Бот найден: @{me.username}")
        print(f"   ID: {me.id}")
        print(f"   Имя: {me.first_name}")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        print(f"🌐 Webhook: {webhook_info.url or 'не установлен'}")
        
        # Закрываем сессию
        await bot.session.close()
        
        print("✅ Базовый тест пройден!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def test_storage():
    """Тест системы хранения данных."""
    print("\n💾 ТЕСТ СИСТЕМЫ ХРАНЕНИЯ")
    print("=" * 40)
    
    try:
        from app.services.storage import Storage
        
        storage = Storage()
        data = storage.load()
        
        print(f"✅ Данные загружены:")
        print(f"   Пользователи: {len(data.get('users', {}))}")
        print(f"   Очередь: {len(data.get('queue', []))}")
        print(f"   Команды: {len(data.get('teams', {}))}")
        print(f"   Админы: {len(data.get('admins', {}))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка хранения: {e}")
        return False

async def test_handlers():
    """Тест загрузки обработчиков."""
    print("\n🎯 ТЕСТ ОБРАБОТЧИКОВ")
    print("=" * 40)
    
    try:
        # Импортируем основные компоненты
        from app.bot import bot, dp
        
        print("✅ Бот и диспетчер импортированы")
        
        # Проверяем зарегистрированные роутеры
        router_count = len(dp.sub_routers)
        print(f"✅ Зарегистрировано роутеров: {router_count}")
        
        # Проверяем наличие обработчика /start
        from app.handlers import user_start
        print("✅ Обработчик /start найден")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обработчиков: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_debug_info():
    """Выводит отладочную информацию."""
    print("\n🔍 ОТЛАДОЧНАЯ ИНФОРМАЦИЯ")
    print("=" * 40)
    
    print(f"Python версия: {sys.version}")
    print(f"Рабочая директория: {os.getcwd()}")
    
    # Проверяем переменные окружения
    important_vars = ['BOT_TOKEN', 'ADMIN_CODE', 'USE_WEBHOOK', 'WEBHOOK_URL']
    for var in important_vars:
        value = os.getenv(var)
        if value:
            if 'TOKEN' in var:
                # Скрываем токен
                display = f"{value[:6]}...{value[-4:]}"
            else:
                display = value
            print(f"   {var}: {display}")
        else:
            print(f"   {var}: НЕ УСТАНОВЛЕН")

async def main():
    """Главная функция."""
    print_debug_info()
    
    # Тесты
    tests_passed = 0
    total_tests = 3
    
    if await test_basic_bot():
        tests_passed += 1
    
    if await test_storage():
        tests_passed += 1
    
    if await test_handlers():
        tests_passed += 1
    
    print(f"\n📊 РЕЗУЛЬТАТ: {tests_passed}/{total_tests} тестов пройдено")
    
    if tests_passed == total_tests:
        print("🎉 Все тесты пройдены! Бот должен работать.")
        print("\n💡 Если бот все еще не отвечает:")
        print("1. Убедитесь, что Repl запущен и не спит")
        print("2. Проверьте правильность имени бота в Telegram")
        print("3. Попробуйте команду /start еще раз")
        print("4. Проверьте логи в консоли Replit")
    else:
        print("❌ Есть проблемы, которые нужно исправить")
    
    return tests_passed == total_tests

if __name__ == '__main__':
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n🔴 Тест прерван")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
