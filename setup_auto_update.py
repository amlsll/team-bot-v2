#!/usr/bin/env python3
"""
Скрипт быстрой настройки системы автоматического обновления.
"""

import os
import sys
import secrets
from pathlib import Path


def generate_secret():
    """Генерирует случайный секретный ключ."""
    return secrets.token_hex(32)


def update_env_file():
    """Обновляет .env файл с настройками автообновления."""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ Файл .env не найден. Создайте его на основе env.sample")
        return False
    
    # Читаем существующий .env
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Проверяем, есть ли уже настройки автообновления
    has_auto_update = any('AUTO_UPDATE_ENABLED' in line for line in lines)
    
    if has_auto_update:
        print("ℹ️ Настройки автообновления уже присутствуют в .env")
        return True
    
    # Генерируем секретный ключ
    secret = generate_secret()
    
    # Добавляем настройки автообновления
    auto_update_config = f"""
# === НАСТРОЙКИ АВТООБНОВЛЕНИЯ ===

# Включить автоматическое обновление из GitHub (по умолчанию false)
AUTO_UPDATE_ENABLED=true

# Ветка для автоматического обновления (по умолчанию main)
UPDATE_BRANCH=main

# Секретный ключ для проверки GitHub webhook (рекомендуется)
GITHUB_WEBHOOK_SECRET={secret}
"""
    
    # Записываем обновленный файл
    with open(env_path, 'a', encoding='utf-8') as f:
        f.write(auto_update_config)
    
    print("✅ Настройки автообновления добавлены в .env")
    print(f"🔑 Сгенерирован секретный ключ: {secret}")
    print("⚠️ Используйте этот ключ при настройке GitHub webhook")
    
    return True


def create_systemd_service():
    """Создает пример systemd сервиса."""
    project_path = Path.cwd().resolve()
    python_path = sys.executable
    
    service_content = f"""[Unit]
Description=Team Bot Auto Deploy Service
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'your_user')}
WorkingDirectory={project_path}
ExecStart={python_path} auto_deploy.py
Restart=always
RestartSec=10
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH={project_path}

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path('team-bot.service')
    with open(service_path, 'w', encoding='utf-8') as f:
        f.write(service_content)
    
    print(f"✅ Создан файл сервиса: {service_path}")
    print("📝 Для установки выполните:")
    print(f"   sudo cp {service_path} /etc/systemd/system/")
    print("   sudo systemctl enable team-bot")
    print("   sudo systemctl start team-bot")


def create_docker_compose():
    """Создает пример docker-compose.yml."""
    compose_content = """version: '3.8'

services:
  team-bot:
    build: .
    restart: unless-stopped
    volumes:
      - .:/app
      - ./data:/app/data
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - ADMIN_CODE=${ADMIN_CODE}
      - AUTO_UPDATE_ENABLED=true
      - UPDATE_BRANCH=main
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - USE_WEBHOOK=true
      - WEBHOOK_URL=${WEBHOOK_URL}
      - PORT=3000
    ports:
      - "3000:3000"
    networks:
      - bot-network

networks:
  bot-network:
    driver: bridge
"""
    
    dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Установка git для автообновлений
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для данных
RUN mkdir -p /app/data

# Запуск автодеплоя
CMD ["python", "auto_deploy.py"]
"""
    
    Path('docker-compose.yml').write_text(compose_content, encoding='utf-8')
    Path('Dockerfile').write_text(dockerfile_content, encoding='utf-8')
    
    print("✅ Созданы файлы Docker: docker-compose.yml, Dockerfile")


def print_webhook_instructions(secret):
    """Выводит инструкции по настройке GitHub webhook."""
    print("\n🔧 НАСТРОЙКА GITHUB WEBHOOK:")
    print("1. Перейдите в настройки вашего GitHub репозитория")
    print("2. Settings → Webhooks → Add webhook")
    print("3. Заполните поля:")
    print("   Payload URL: https://yourdomain.com/github-webhook")
    print("   Content type: application/json")
    print(f"   Secret: {secret}")
    print("   Events: Just the push event")
    print("4. Нажмите Add webhook")


def main():
    """Основная функция настройки."""
    print("🚀 НАСТРОЙКА АВТОМАТИЧЕСКОГО ОБНОВЛЕНИЯ TEAM-BOT")
    print("=" * 50)
    
    # Проверяем, что мы в правильной директории
    if not Path('app/bot.py').exists():
        print("❌ Запустите скрипт из корневой директории проекта team-bot")
        return 1
    
    try:
        # Обновляем .env файл
        if not update_env_file():
            return 1
        
        print("\n📋 ВЫБЕРИТЕ СПОСОБ ДЕПЛОЯ:")
        print("1. Systemd сервис (Linux)")
        print("2. Docker compose")
        print("3. Только настройка .env (ручной запуск)")
        
        choice = input("\nВведите номер (1-3): ").strip()
        
        if choice == '1':
            create_systemd_service()
        elif choice == '2':
            create_docker_compose()
        elif choice == '3':
            print("✅ Настройка .env завершена")
        else:
            print("⚠️ Неверный выбор, создаются только настройки .env")
        
        # Читаем секретный ключ из .env для инструкций
        secret = None
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('GITHUB_WEBHOOK_SECRET='):
                    secret = line.split('=', 1)[1].strip()
                    break
        
        if secret:
            print_webhook_instructions(secret)
        
        print("\n✅ НАСТРОЙКА ЗАВЕРШЕНА!")
        print("\n📚 Для подробной информации см. AUTO_UPDATE_GUIDE.md")
        print("\n🎛️ Доступные админские команды:")
        print("   /adm_update_check - проверить обновления")
        print("   /adm_update_apply - применить обновления")
        print("   /adm_restart - перезапустить бота")
        print("   /adm_status - статус бота")
        
        return 0
        
    except Exception as e:
        print(f"❌ Ошибка настройки: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
