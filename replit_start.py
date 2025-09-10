#!/usr/bin/env python3
"""
Специальный скрипт запуска для Replit.
Автоматически настраивает webhook режим для Cloud Run деплоя.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def setup_replit_environment():
    """Настройка окружения для Replit."""
    logger.info("🔧 Настройка окружения для Replit...")
    
    # Проверяем обязательные переменные
    bot_token = os.getenv('BOT_TOKEN')
    admin_code = os.getenv('ADMIN_CODE')
    
    if not bot_token:
        logger.error("❌ BOT_TOKEN не найден в переменных окружения")
        logger.error("💡 Добавьте BOT_TOKEN в Secrets (🔒 иконка слева)")
        sys.exit(1)
    
    if not admin_code:
        logger.error("❌ ADMIN_CODE не найден в переменных окружения") 
        logger.error("💡 Добавьте ADMIN_CODE в Secrets (🔒 иконка слева)")
        sys.exit(1)
    
    # Проверяем, установлен ли уже WEBHOOK_URL
    existing_webhook = os.getenv('WEBHOOK_URL')
    
    if existing_webhook:
        logger.info(f"✅ Использую существующий WEBHOOK_URL: {existing_webhook}")
        webhook_url = existing_webhook
    else:
        # Определяем webhook URL на основе Replit домена
        replit_domain = os.getenv('REPLIT_DEV_DOMAIN')
        repl_slug = os.getenv('REPL_SLUG', 'team-bot-v2')
        repl_owner = os.getenv('REPL_OWNER', 'user')
        
        if replit_domain:
            webhook_url = f"https://{replit_domain}/webhook"
            logger.info(f"✅ Автоматически определен Webhook URL: {webhook_url}")
        else:
            # Формируем webhook URL для Replit
            webhook_url = f"https://{repl_slug}.{repl_owner}.repl.co/webhook"
            logger.info(f"✅ Сгенерированный Webhook URL: {webhook_url}")
    
    # Настройка режима работы: webhook по умолчанию для стабильности
    use_webhook = os.getenv('USE_WEBHOOK', 'true').lower() == 'true'
    os.environ['USE_WEBHOOK'] = 'true' if use_webhook else 'false'
    os.environ['WEBHOOK_URL'] = webhook_url
    os.environ['PORT'] = '8080'
    
    use_webhook_display = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
    logger.info(f"✅ Режим: {'webhook' if use_webhook_display else 'polling'}")
    logger.info(f"✅ Port: {os.environ.get('PORT', '3000')}")
    
    return webhook_url

async def main():
    """Главная функция запуска для Replit."""
    logger.info("🚀 Запуск team-bot для Replit...")
    
    try:
        # Настраиваем окружение для Replit
        webhook_url = setup_replit_environment()
        
        # Проверяем режим работы
        use_webhook = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
        
        if use_webhook:
            logger.info("🌐 Запуск в webhook режиме...")
            # Запускаем webhook сервер  
            from aiohttp import web
            from app.__main__ import webhook_main
            
            app, port = await webhook_main()
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            
            logger.info(f"🚀 Webhook сервер запущен на 0.0.0.0:{port}")
            
            # Ждем бесконечно
            while True:
                await asyncio.sleep(3600)
        else:
            logger.info("📡 Запуск в polling режиме...")
            # Запускаем в polling режиме
            from app.__main__ import polling_main
            await polling_main()
            
    except KeyboardInterrupt:
        logger.info("🔴 Получен сигнал прерывания")
        return 0
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)