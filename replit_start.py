#!/usr/bin/env python3
"""
Replit Cloud Run специальный стартер для Telegram бота
Автоматически настраивает webhook режим для развертывания
"""

import os
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Устанавливаем переменные окружения для Replit Cloud Run
logger.info("🚀 Настройка team-bot для Replit Cloud Run...")

# Принудительно устанавливаем webhook режим для Replit
os.environ['USE_WEBHOOK'] = 'true'
os.environ['PORT'] = '3000'  # Стандартный порт для Replit Cloud Run

# Определяем webhook URL на основе Replit домена
replit_domain = os.getenv('REPLIT_DEV_DOMAIN')
if replit_domain:
    webhook_url = f"https://{replit_domain}/webhook"
    os.environ['WEBHOOK_URL'] = webhook_url
    logger.info(f"🌐 Webhook URL установлен: {webhook_url}")
else:
    logger.warning("⚠️ REPLIT_DEV_DOMAIN не найден, webhook URL может быть не установлен")

# Импортируем и запускаем основной модуль напрямую
if __name__ == '__main__':
    # Запускаем app.__main__ напрямую, все переменные уже установлены
    import asyncio
    from app.__main__ import main as bot_main
    
    # Создаем новый event loop для webhook
    try:
        asyncio.run(bot_main())
    except RuntimeError as e:
        if "Cannot run the event loop while another loop is running" in str(e):
            # Если event loop уже запущен, запускаем в существующем
            loop = asyncio.get_event_loop()
            loop.run_until_complete(bot_main())
        else:
            raise