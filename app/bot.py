"""
Создание экземпляра бота, диспетчера и настройка middlewares.
"""

import os
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Инициализируем систему логирования
from .services.logger import bot_logger, get_logger

# Запускаем периодическое логирование метрик
bot_logger.start_metrics_logging(interval=300)  # каждые 5 минут

logger = get_logger('bot')

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# Создаем экземпляр бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Создаем диспетчер с поддержкой FSM
dp = Dispatcher(storage=MemoryStorage())


# Импортируем и регистрируем handlers сразу
from .handlers import (
    user_start, user_status, user_leave,
    admin_core, admin_match, admin_stats,
    admin_rematch, admin_broadcast, admin_change, admin_questions, team_actions,
    auto_update, admin_restart, admin_monitoring, fallback
)

# Регистрируем роутеры обработчиков
dp.include_router(user_start.router)
dp.include_router(user_status.router)
dp.include_router(user_leave.router)
dp.include_router(team_actions.router)
dp.include_router(admin_core.router)
dp.include_router(admin_match.router)
dp.include_router(admin_stats.router)
dp.include_router(admin_rematch.router)
dp.include_router(admin_broadcast.router)
dp.include_router(admin_change.router)
dp.include_router(admin_questions.router)
dp.include_router(admin_monitoring.router)
dp.include_router(auto_update.router)
dp.include_router(admin_restart.router)
# Fallback хендлер должен быть последним
dp.include_router(fallback.router)

# Подключаем middleware для обработки ошибок и мониторинга
from .middlewares.error_handler import ErrorHandlerMiddleware, PerformanceMiddleware
dp.message.middleware(PerformanceMiddleware(slow_threshold_ms=500))
dp.callback_query.middleware(PerformanceMiddleware(slow_threshold_ms=500))
dp.message.middleware(ErrorHandlerMiddleware())
dp.callback_query.middleware(ErrorHandlerMiddleware())

logger.info("Handlers зарегистрированы")
logger.info("Middleware подключены")


async def on_startup():
    """Выполняется при запуске бота."""
    from .services.scheduler import MatchScheduler
    
    logger.info("🚀 Запуск бота...")
    
    # Проверяем webhook только в polling режиме
    use_webhook = os.getenv('USE_WEBHOOK', 'false').lower() == 'true'
    
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url and not use_webhook:
            logger.info(f"Обнаружен активный webhook в polling режиме: {webhook_info.url}")
            await bot.delete_webhook()
            logger.info("Webhook удален для polling режима")
        elif webhook_info.url and use_webhook:
            logger.info(f"✅ Webhook активен: {webhook_info.url}")
        elif use_webhook:
            logger.info("⚠️ Webhook режим, но URL не установлен (устанавливается в webhook_main)")
    except Exception as e:
        logger.warning(f"Ошибка при проверке webhook: {e}")
    
    # Проверяем работоспособность бота
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот подключен: @{me.username} ({me.first_name})")
        
        # Настраиваем команды бота для меню
        from aiogram.types import BotCommand
        commands = [
            BotCommand(command="start", description="🚀 Начать работу с ботом"),
            BotCommand(command="status", description="📊 Проверить статус"),
            BotCommand(command="leave", description="❌ Покинуть очередь/команду"),
        ]
        await bot.set_my_commands(commands)
        logger.info("✅ Команды бота настроены")
        
        # Устанавливаем описание бота
        await bot.set_my_description(
            "🤝 Бот для объединения волонтеров в команды для участия в конкурсе «Доброе Сердце Столицы»\n\n"
            "Нажми /start чтобы начать!"
        )
        
        # Устанавливаем краткое описание
        await bot.set_my_short_description(
            "Объединение волонтеров в команды для конкурса"
        )
        logger.info("✅ Описание бота настроено")
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения бота: {e}")
        raise
    
    # Создаем и запускаем планировщик
    try:
        scheduler = MatchScheduler(bot)
        scheduler.start()
        
        # Сохраняем ссылку на планировщик в диспетчере
        dp['scheduler'] = scheduler
        logger.info("📅 Планировщик автоматического объединения команд активирован")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")
        # Продолжаем работу без планировщика
    
    # Запускаем мониторинг здоровья
    try:
        from .services.health_monitor import health_monitor
        health_monitor.bot = bot
        
        # Запускаем мониторинг в фоновом режиме
        asyncio.create_task(health_monitor.start_monitoring())
        
        dp['health_monitor'] = health_monitor
        logger.info("🏥 Мониторинг здоровья бота активирован")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска мониторинга здоровья: {e}")
        # Продолжаем работу без мониторинга
    
    logger.info("🎉 Бот запущен и готов к работе!")
    logger.info("🔄 Ожидание сообщений...")


async def on_shutdown():
    """Выполняется при остановке бота."""
    # Останавливаем планировщик
    scheduler = dp.get('scheduler')
    if scheduler:
        scheduler.stop()
    
    # Останавливаем мониторинг здоровья
    health_monitor = dp.get('health_monitor')
    if health_monitor:
        health_monitor.stop_monitoring()
    
    logger.info("Бот остановлен")


# Регистрируем startup/shutdown хуки
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)
