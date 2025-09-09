"""
Точка входа для запуска бота: python -m app
"""

import asyncio
import os
import logging
import signal
import sys
from dotenv import load_dotenv

from .bot import bot, dp

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)


async def webhook_main():
    """Запуск бота через webhook."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    
    webhook_url = os.getenv('WEBHOOK_URL')
    port = int(os.getenv('PORT', 3000))
    
    if not webhook_url:
        raise ValueError("WEBHOOK_URL не найден в переменных окружения при USE_WEBHOOK=true")
    
    # Устанавливаем webhook
    await bot.set_webhook(webhook_url)
    
    # Создаем aiohttp приложение
    app = web.Application()
    
    # Создаем handler для webhook
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    
    # Регистрируем webhook
    webhook_handler.register(app, path="/webhook")
    
    # Регистрируем GitHub webhook для автообновлений
    from .handlers.auto_update import setup_github_webhook
    setup_github_webhook(app, "/github-webhook")
    
    # Добавляем health check endpoint для Replit
    async def health_check(request):
        return web.json_response({"status": "ok", "bot": "@mosvolteambot", "mode": "webhook"})
    
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    # Настраиваем приложение
    setup_application(app, dp, bot=bot)
    
    # Запускаем сервер
    return app, port


async def polling_main():
    """Запуск бота через long polling."""
    logger.info("📡 Запуск в режиме long polling...")
    
    # Обработчики сигналов для graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Получен сигнал {sig}, завершаем работу...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Проверяем состояние перед запуском
        me = await bot.get_me()
        logger.info(f"✅ Подключение к Telegram API успешно: @{me.username}")
        
        # Очищаем webhook если он был установлен
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.info(f"Очищаем webhook: {webhook_info.url}")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook очищен")
        
        await dp.start_polling(bot, handle_signals=False)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        raise


async def main():
    """Главная функция запуска."""
    logger.info("🚀 Запуск team-bot...")
    
    try:
        use_webhook = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
        logger.info(f"Моде работы: {'webhook' if use_webhook else 'polling'}")
        
        if use_webhook:
            app, port = await webhook_main()
            from aiohttp import web
            logger.info(f"🌐 Запуск webhook сервера на порту {port}")
            web.run_app(app, host='0.0.0.0', port=port)
        else:
            await polling_main()
            
    except KeyboardInterrupt:
        logger.info("🔴 Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        raise
    finally:
        logger.info("🔴 Бот остановлен")


if __name__ == '__main__':
    asyncio.run(main())
