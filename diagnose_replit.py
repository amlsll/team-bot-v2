#!/usr/bin/env python3
"""
Скрипт диагностики проблем team-bot на Replit.
Проверяет все ключевые компоненты и помогает найти причину, почему бот не реагирует на /start.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования для диагностики
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def check_environment():
    """Проверяет окружение Replit."""
    print("🔍 ПРОВЕРКА ОКРУЖЕНИЯ")
    print("=" * 50)
    
    # Проверка Replit окружения
    replit_vars = ['REPL_ID', 'REPL_SLUG', 'REPL_OWNER', 'REPLIT_DB_URL']
    is_replit = any(var in os.environ for var in replit_vars)
    
    if is_replit:
        print("✅ Окружение Replit обнаружено")
        for var in replit_vars:
            value = os.getenv(var)
            if value:
                print(f"   {var}: {value}")
    else:
        print("❌ Окружение Replit НЕ обнаружено")
        print("   Возможно, скрипт запущен локально")
    
    # Проверка текущей директории
    current_dir = os.getcwd()
    print(f"📁 Текущая директория: {current_dir}")
    
    # Проверка файлов проекта
    required_files = ['replit_start.py', 'requirements.txt', '.replit', 'replit.nix']
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} найден")
        else:
            print(f"❌ {file} НЕ найден")
            missing_files.append(file)
    
    if missing_files:
        print(f"⚠️ Отсутствующие файлы: {', '.join(missing_files)}")
    
    return is_replit, missing_files

def check_env_variables():
    """Проверяет переменные окружения."""
    print("\n🔐 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    print("=" * 50)
    
    # Загружаем .env файл если есть
    load_dotenv()
    
    # Критически важные переменные
    critical_vars = {
        'BOT_TOKEN': 'Токен Telegram бота',
        'ADMIN_CODE': 'Код для получения прав администратора'
    }
    
    # Важные переменные для Replit
    replit_vars = {
        'USE_WEBHOOK': 'Режим webhook',
        'WEBHOOK_URL': 'URL для webhook',
        'PORT': 'Порт для сервера',
        'AUTO_UPDATE_ENABLED': 'Автообновление',
        'UPDATE_BRANCH': 'Ветка для обновления'
    }
    
    missing_critical = []
    
    print("🔴 КРИТИЧЕСКИ ВАЖНЫЕ:")
    for var, desc in critical_vars.items():
        value = os.getenv(var)
        if value:
            # Показываем только первые и последние символы токена
            if 'TOKEN' in var and len(value) > 10:
                display_value = f"{value[:6]}...{value[-6:]}"
            else:
                display_value = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: НЕ УСТАНОВЛЕН ({desc})")
            missing_critical.append(var)
    
    print("\n🟡 НАСТРОЙКИ REPLIT:")
    for var, desc in replit_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: не установлен ({desc})")
    
    return missing_critical

def check_data_file():
    """Проверяет файл данных."""
    print("\n📄 ПРОВЕРКА ФАЙЛА ДАННЫХ")
    print("=" * 50)
    
    data_file = Path('data.json')
    
    if not data_file.exists():
        print("❌ data.json НЕ найден")
        return False
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("✅ data.json найден и корректен")
        print(f"   Пользователи: {len(data.get('users', {}))}")
        print(f"   Очередь: {len(data.get('queue', []))}")
        print(f"   Команды: {len(data.get('teams', {}))}")
        print(f"   Админы: {len(data.get('admins', {}))}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ data.json поврежден: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка чтения data.json: {e}")
        return False

async def test_bot_connection():
    """Тестирует подключение к Telegram API."""
    print("\n🤖 ТЕСТ ПОДКЛЮЧЕНИЯ К TELEGRAM")
    print("=" * 50)
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN не найден - тест невозможен")
        return False
    
    try:
        from aiogram import Bot
        bot = Bot(token=bot_token)
        
        print("🔄 Подключение к Telegram API...")
        me = await bot.get_me()
        
        print(f"✅ Подключение успешно!")
        print(f"   Имя бота: @{me.username}")
        print(f"   ID: {me.id}")
        print(f"   Полное имя: {me.first_name}")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            print(f"🌐 Webhook установлен: {webhook_info.url}")
            print(f"   Ожидающих обновлений: {webhook_info.pending_update_count}")
        else:
            print("📡 Webhook не установлен (polling режим)")
        
        await bot.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def check_webhook_setup():
    """Проверяет настройки webhook."""
    print("\n🌐 ПРОВЕРКА НАСТРОЕК WEBHOOK")
    print("=" * 50)
    
    use_webhook = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
    webhook_url = os.getenv('WEBHOOK_URL')
    port = os.getenv('PORT', '3000')
    
    print(f"Режим webhook: {'ВКЛ' if use_webhook else 'ВЫКЛ'}")
    
    if use_webhook:
        if webhook_url:
            print(f"✅ WEBHOOK_URL: {webhook_url}")
            
            # Проверяем формат URL
            if 'repl.co' in webhook_url:
                print("✅ URL похож на Replit URL")
            else:
                print("⚠️ URL не похож на Replit URL")
            
            print(f"✅ PORT: {port}")
            
            # Проверяем, что URL оканчивается правильно
            if not webhook_url.endswith('.repl.co'):
                print("⚠️ WEBHOOK_URL должен заканчиваться на .repl.co для Replit")
            
        else:
            print("❌ WEBHOOK_URL не установлен (обязателен для webhook режима)")
            return False
    else:
        print("📡 Режим polling - webhook настройки не требуются")
    
    return True

def check_replit_files():
    """Проверяет специфичные для Replit файлы."""
    print("\n📋 ПРОВЕРКА ФАЙЛОВ REPLIT")
    print("=" * 50)
    
    # Проверяем .replit
    replit_file = Path('.replit')
    if replit_file.exists():
        print("✅ .replit найден")
        try:
            content = replit_file.read_text()
            if 'replit_start.py' in content:
                print("✅ .replit настроен на запуск через replit_start.py")
            else:
                print("⚠️ .replit может быть настроен неправильно")
        except Exception as e:
            print(f"⚠️ Не удалось прочитать .replit: {e}")
    else:
        print("❌ .replit НЕ найден")
    
    # Проверяем replit.nix
    nix_file = Path('replit.nix')
    if nix_file.exists():
        print("✅ replit.nix найден")
    else:
        print("❌ replit.nix НЕ найден")
    
    # Проверяем requirements.txt
    req_file = Path('requirements.txt')
    if req_file.exists():
        print("✅ requirements.txt найден")
        try:
            content = req_file.read_text()
            if 'aiogram' in content:
                print("✅ aiogram найден в зависимостях")
            else:
                print("❌ aiogram НЕ найден в зависимостях")
        except Exception as e:
            print(f"⚠️ Не удалось прочитать requirements.txt: {e}")
    else:
        print("❌ requirements.txt НЕ найден")

def generate_recommendations(missing_critical, missing_files, webhook_ok, bot_connection_ok):
    """Генерирует рекомендации по исправлению проблем."""
    print("\n💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ")
    print("=" * 50)
    
    if missing_critical:
        print("🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
        for var in missing_critical:
            if var == 'BOT_TOKEN':
                print("❌ Установите BOT_TOKEN в Secrets Replit:")
                print("   1. Откройте 🔒 Secrets в левой панели Replit")
                print("   2. Добавьте ключ: BOT_TOKEN")
                print("   3. Значение: токен от @BotFather")
            elif var == 'ADMIN_CODE':
                print("❌ Установите ADMIN_CODE в Secrets Replit:")
                print("   1. Откройте 🔒 Secrets в левой панели Replit")
                print("   2. Добавьте ключ: ADMIN_CODE")
                print("   3. Значение: любой секретный код для админов")
    
    if missing_files:
        print("\n🟡 ОТСУТСТВУЮЩИЕ ФАЙЛЫ:")
        print("❌ Возможно, репозиторий склонирован не полностью")
        print("   Пересоздайте Repl из GitHub с полным репозиторием")
    
    if not webhook_ok:
        print("\n🌐 ПРОБЛЕМЫ С WEBHOOK:")
        print("❌ Проверьте настройки webhook в Secrets:")
        print("   USE_WEBHOOK=true")
        print("   WEBHOOK_URL=https://ваш-repl-name.ваш-username.repl.co")
        print("   PORT=3000")
    
    if not bot_connection_ok:
        print("\n🤖 ПРОБЛЕМЫ С ПОДКЛЮЧЕНИЕМ:")
        print("❌ Бот не может подключиться к Telegram:")
        print("   1. Проверьте правильность BOT_TOKEN")
        print("   2. Убедитесь, что токен активен (@BotFather)")
        print("   3. Проверьте интернет-соединение Replit")
    
    if not any([missing_critical, missing_files, not webhook_ok, not bot_connection_ok]):
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("\nВозможные причины, почему бот не отвечает:")
        print("1. 🛌 Repl заснул - нажмите Run еще раз")
        print("2. 📱 Используйте правильное имя бота (@имя_вашего_бота)")
        print("3. 🔄 Попробуйте перезапустить Repl")
        print("4. 📊 Проверьте логи в консоли Replit")
        print("5. ⏰ Включите Always On в настройках Replit")

async def main():
    """Основная функция диагностики."""
    print("🔧 ДИАГНОСТИКА TEAM-BOT НА REPLIT")
    print("=" * 60)
    
    # Проверки
    is_replit, missing_files = check_environment()
    missing_critical = check_env_variables()
    data_ok = check_data_file()
    webhook_ok = check_webhook_setup()
    check_replit_files()
    
    # Тест подключения к боту (только если есть токен)
    bot_connection_ok = False
    if not missing_critical or 'BOT_TOKEN' not in missing_critical:
        bot_connection_ok = await test_bot_connection()
    
    # Генерация рекомендаций
    generate_recommendations(missing_critical, missing_files, webhook_ok, bot_connection_ok)
    
    print("\n" + "=" * 60)
    print("📋 БЫСТРЫЙ ЧЕКЛИСТ ДЛЯ REPLIT:")
    print("1. ✅ Установить BOT_TOKEN и ADMIN_CODE в Secrets")
    print("2. ✅ Установить USE_WEBHOOK=true в Secrets")  
    print("3. ✅ Установить WEBHOOK_URL=https://ваш-repl.repl.co в Secrets")
    print("4. ✅ Нажать Run в Replit")
    print("5. ✅ Включить Always On для 24/7 работы")
    print("6. ✅ Написать боту /start в Telegram")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔴 Диагностика прервана")
    except Exception as e:
        print(f"\n❌ Ошибка диагностики: {e}")
        import traceback
        traceback.print_exc()
