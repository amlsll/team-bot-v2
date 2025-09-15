#!/usr/bin/env python3
"""
Специальный скрипт запуска для Replit.
Автоматически настраивает webhook режим для Cloud Run деплоя.
"""

import os
import sys
import asyncio
import logging
import aiohttp
import json
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import time

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


# ========================================
# KEEP-ALIVE СЕРВЕР ДЛЯ ПРЕДОТВРАЩЕНИЯ ЗАСЫПАНИЯ
# ========================================

def create_keep_alive_server():
    """Создает Flask сервер для поддержания активности Replit VM."""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        """Главная страница Keep-Alive сервера."""
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        return f"""
        <html>
        <head>
            <title>Team Bot Keep-Alive</title>
            <meta http-equiv="refresh" content="30">
        </head>
        <body>
            <h1>🤖 Team Bot Keep-Alive Server</h1>
            <p>✅ Bot is running and healthy!</p>
            <p>🕐 Current time: {current_time}</p>
            <p>🔄 This page auto-refreshes every 30 seconds</p>
            <p>📡 Use this URL for UptimeRobot monitoring</p>
        </body>
        </html>
        """
    
    @app.route('/health')
    def health():
        """Endpoint для проверки здоровья."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "telegram-bot-keep-alive"
        }
    
    @app.route('/ping')
    def ping():
        """Простой ping endpoint."""
        return "pong"
    
    # Отключаем логи Flask для чистоты вывода
    import logging as flask_logging
    flask_log = flask_logging.getLogger('werkzeug')
    flask_log.setLevel(flask_logging.ERROR)
    
    return app


def start_keep_alive_server():
    """Запускает Keep-Alive сервер в отдельном треде."""
    try:
        app = create_keep_alive_server()
        # Запускаем на порту 8080, чтобы не конфликтовать с основным webhook (3000)
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Keep-Alive сервера: {e}")


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
    os.environ['PORT'] = '3000'  # Используем порт 3000 который маппится на externalPort 80
    
    use_webhook_display = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
    logger.info(f"✅ Режим: {'webhook' if use_webhook_display else 'polling'}")
    logger.info(f"✅ Port: {os.environ.get('PORT', '3000')}")
    
    return webhook_url


async def verify_and_update_webhook(webhook_url: str) -> bool:
    """
    Проверяет текущий webhook URL в Telegram и обновляет его при необходимости.
    
    Returns:
        bool: True если webhook корректно настроен, False если произошла ошибка
    """
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("❌ BOT_TOKEN недоступен для проверки webhook")
        return False
    
    try:
        # Проверяем текущий webhook
        async with aiohttp.ClientSession() as session:
            # Получаем информацию о текущем webhook
            get_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            async with session.get(get_url) as response:
                if response.status != 200:
                    logger.error(f"❌ Ошибка при получении webhook info: {response.status}")
                    return False
                
                data = await response.json()
                if not data.get('ok'):
                    logger.error(f"❌ Telegram API ошибка: {data.get('description')}")
                    return False
                
                webhook_info = data.get('result', {})
                current_url = webhook_info.get('url')
                pending_count = webhook_info.get('pending_update_count', 0)
                last_error = webhook_info.get('last_error_message')
                
                logger.info(f"🔍 Текущий webhook: {current_url or 'не установлен'}")
                if pending_count > 0:
                    logger.warning(f"⚠️ Ожидающих обновлений: {pending_count}")
                if last_error:
                    logger.warning(f"⚠️ Последняя ошибка: {last_error}")
                
                # Проверяем, нужно ли обновлять webhook
                if current_url == webhook_url:
                    logger.info("✅ Webhook URL корректен, обновление не требуется")
                    return True
                
                # Обновляем webhook URL
                logger.info(f"🔄 Обновляем webhook URL: {current_url} → {webhook_url}")
                set_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
                set_data = {
                    'url': webhook_url,
                    'allowed_updates': ['message', 'callback_query']
                }
                
                async with session.post(set_url, data=set_data) as set_response:
                    if set_response.status != 200:
                        logger.error(f"❌ Ошибка при установке webhook: {set_response.status}")
                        return False
                    
                    set_result = await set_response.json()
                    if not set_result.get('ok'):
                        logger.error(f"❌ Ошибка установки webhook: {set_result.get('description')}")
                        return False
                    
                    logger.info("✅ Webhook URL успешно обновлен")
                    
                    # Повторная проверка
                    async with session.get(get_url) as verify_response:
                        if verify_response.status == 200:
                            verify_data = await verify_response.json()
                            if verify_data.get('ok'):
                                verify_info = verify_data.get('result', {})
                                new_url = verify_info.get('url')
                                new_pending = verify_info.get('pending_update_count', 0)
                                
                                logger.info(f"🔍 Проверка: webhook установлен на {new_url}")
                                if new_pending > 0:
                                    logger.info(f"📬 Обрабатываем {new_pending} ожидающих обновлений")
                    
                    return True
                    
    except aiohttp.ClientError as e:
        logger.error(f"❌ Сетевая ошибка при работе с webhook: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Непредвиденная ошибка при проверке webhook: {e}")
        return False

async def main():
    """Главная функция запуска для Replit."""
    logger.info("🚀 Запуск team-bot для Replit...")
    
    # ========================================
    # ЗАПУСК KEEP-ALIVE СЕРВЕРА
    # ========================================
    logger.info("🔄 Запуск Keep-Alive сервера...")
    keep_alive_thread = Thread(target=start_keep_alive_server, daemon=True)
    keep_alive_thread.start()
    logger.info("✅ Keep-Alive сервер запущен на порту 8080")
    
    # Защита от множественных экземпляров
    try:
        from app.services.process_lock import ProcessLock
        
        with ProcessLock("team_bot_replit") as lock:
            # Настраиваем окружение для Replit
            webhook_url = setup_replit_environment()
            
            # Проверяем режим работы
            use_webhook = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
            
            # Автоматическая проверка и обновление webhook при необходимости
            if use_webhook:
                logger.info("🔍 Проверяем и обновляем webhook URL...")
                webhook_ok = await verify_and_update_webhook(webhook_url)
                if not webhook_ok:
                    logger.warning("⚠️ Проблемы с webhook, но продолжаем запуск...")
                else:
                    logger.info("✅ Webhook готов к работе")
            
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
    
    except RuntimeError as e:
        logger.error(f"❌ {e}")
        logger.info("💡 Для исправления остановите все экземпляры бота и перезапустите")
        return 1
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