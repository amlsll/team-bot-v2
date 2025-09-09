#!/usr/bin/env python3
"""
Скрипт настройки team-bot для Replit.
"""

import os
import sys
from pathlib import Path


def check_replit_environment():
    """Проверяет, запущен ли скрипт в Replit."""
    return 'REPL_ID' in os.environ or 'REPLIT_DB_URL' in os.environ


def print_replit_secrets():
    """Выводит список секретов для настройки в Replit."""
    secrets = {
        'BOT_TOKEN': 'Ваш токен бота от @BotFather (НЕ ПУБЛИКУЙТЕ!)',
        'ADMIN_CODE': 'Ваш секретный админ-код (НЕ ПУБЛИКУЙТЕ!)',
        'AUTO_UPDATE_ENABLED': 'true',
        'UPDATE_BRANCH': 'main',
        'GITHUB_WEBHOOK_SECRET': 'Сгенерируйте случайную строку (НЕ ИСПОЛЬЗУЙТЕ ПРИМЕР!)',
        'USE_WEBHOOK': 'true',
        'WEBHOOK_URL': 'https://ваш-repl-name.ваш-username.repl.co',
        'PORT': '3000'
    }
    
    print("🔐 НАСТРОЙКА SECRETS В REPLIT:")
    print("Перейдите в Secrets (🔒 иконка слева) и добавьте:")
    print("⚠️  ВАЖНО: Никогда не публикуйте эти значения в коде!")
    print()
    
    for key, value in secrets.items():
        print(f"Ключ: {key}")
        print(f"Значение: {value}")
        print("-" * 50)


def create_replit_config():
    """Создает конфигурационные файлы для Replit."""
    # Проверяем .replit файл
    replit_file = Path('.replit')
    if replit_file.exists():
        print("✅ .replit файл уже существует")
    else:
        print("❌ .replit файл не найден")
        return False
    
    # Проверяем replit.nix файл
    nix_file = Path('replit.nix')
    if nix_file.exists():
        print("✅ replit.nix файл уже существует")
    else:
        print("❌ replit.nix файл не найден")
        return False
    
    return True


def get_replit_url():
    """Получает URL Replit проекта."""
    repl_id = os.getenv('REPL_ID')
    repl_owner = os.getenv('REPL_OWNER')
    repl_name = os.getenv('REPL_SLUG')
    
    if repl_id and repl_owner and repl_name:
        return f"https://{repl_name}.{repl_owner}.repl.co"
    
    return None


def print_github_webhook_instructions():
    """Выводит инструкции по настройке GitHub webhook."""
    url = get_replit_url()
    if url:
        webhook_url = f"{url}/github-webhook"
    else:
        webhook_url = "https://ваш-repl-name.ваш-username.repl.co/github-webhook"
    
    print("\n🔧 НАСТРОЙКА GITHUB WEBHOOK:")
    print("1. Перейдите в настройки GitHub репозитория")
    print("2. Settings → Webhooks → Add webhook")
    print("3. Заполните поля:")
    print(f"   Payload URL: {webhook_url}")
    print("   Content type: application/json")
    print("   Secret: [ИСПОЛЬЗУЙТЕ ТОТ ЖЕ SECRET ИЗ REPLIT SECRETS!]")
    print("   Events: Just the push event")
    print("4. Нажмите Add webhook")
    print("⚠️  ВАЖНО: Secret должен совпадать с GITHUB_WEBHOOK_SECRET в Replit!")


def check_dependencies():
    """Проверяет зависимости."""
    requirements_file = Path('requirements.txt')
    if not requirements_file.exists():
        print("❌ requirements.txt не найден")
        return False
    
    print("✅ requirements.txt найден")
    return True


def main():
    """Основная функция."""
    print("🚀 НАСТРОЙКА TEAM-BOT ДЛЯ REPLIT")
    print("=" * 50)
    
    # Проверяем окружение
    if check_replit_environment():
        print("✅ Обнаружено окружение Replit")
        current_url = get_replit_url()
        if current_url:
            print(f"🌐 URL вашего Repl: {current_url}")
    else:
        print("⚠️ Replit окружение не обнаружено")
        print("Этот скрипт оптимизирован для Replit")
    
    print()
    
    # Проверяем файлы
    if not check_dependencies():
        return 1
    
    if not create_replit_config():
        print("❌ Конфигурационные файлы для Replit не найдены")
        print("Убедитесь, что вы клонировали полный репозиторий")
        return 1
    
    print()
    
    # Выводим инструкции по настройке
    print_replit_secrets()
    print()
    print_github_webhook_instructions()
    
    print("\n✅ НАСТРОЙКА ЗАВЕРШЕНА!")
    print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Настройте Secrets в Replit (см. выше)")
    print("2. Настройте GitHub webhook (см. выше)")
    print("3. Нажмите Run в Replit")
    print("4. Включите Always On для 24/7 работы")
    
    print("\n🎛️ АДМИНСКИЕ КОМАНДЫ:")
    print("• /adm_update_check - проверить обновления")
    print("• /adm_update_apply - применить обновления")
    print("• /adm_restart - перезапуск")
    print("• /adm_status - статус системы")
    
    print("\n📚 ДОКУМЕНТАЦИЯ:")
    print("• REPLIT_DEPLOYMENT.md - подробное руководство")
    print("• AUTO_UPDATE_GUIDE.md - настройка автообновления")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
