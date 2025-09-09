#!/usr/bin/env python3
"""
Простой запуск бота в режиме polling для отладки проблем с webhook.
"""
import logging
import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).parent))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('polling.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Запуск бота в режиме polling."""
    logger.info("🚀 Запуск team-bot в polling режиме...")
    
    try:
        # Устанавливаем окружение для polling
        os.environ['USE_WEBHOOK'] = 'false'
        
        # Импортируем и запускаем бота
        logger.info("📚 Импорт модулей...")
        
        # Используем прямой импорт polling_main
        from app.__main__ import polling_main
        logger.info("📡 Запуск бота в polling режиме...")
        
        # Запускаем polling
        await polling_main()
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
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