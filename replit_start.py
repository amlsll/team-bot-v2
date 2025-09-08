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

# Импортируем и запускаем webhook сервер напрямую
if __name__ == '__main__':
    import asyncio
    from aiohttp import web
    from app.__main__ import webhook_main
    
    async def run_webhook_server():
        """Запуск webhook сервера для Replit."""
        try:
            logger.info("🌐 Запуск webhook сервера...")
            app, port = await webhook_main()
            logger.info(f"✅ Webhook сервер готов на порту {port}")
            
            # Запускаем сервер
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            
            logger.info(f"🚀 Сервер запущен на 0.0.0.0:{port}")
            logger.info("🔄 Ожидание webhook запросов...")
            
            # Ждем бесконечно
            while True:
                await asyncio.sleep(3600)  # Спим по часу
                
        except Exception as e:
            logger.error(f"❌ Ошибка webhook сервера: {e}")
            raise
    
    # Запускаем сервер
    asyncio.run(run_webhook_server())