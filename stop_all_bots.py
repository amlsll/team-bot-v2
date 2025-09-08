#!/usr/bin/env python3
"""
Утилита для остановки всех запущенных экземпляров бота.
Использует процесс-менеджер для безопасного завершения процессов.
"""

import sys
import logging
import argparse
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Останавливает все запущенные экземпляры team-bot"
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Принудительное завершение процессов (SIGKILL вместо SIGTERM)'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='Только показать список запущенных процессов без остановки'
    )
    
    args = parser.parse_args()
    
    # Загружаем переменные окружения
    load_dotenv()
    
    try:
        from app.services.process_lock import check_running_instances, stop_all_instances
        
        logger.info("🔍 Поиск запущенных экземпляров бота...")
        
        # Проверяем запущенные процессы
        running_instances = check_running_instances()
        
        if not running_instances:
            logger.info("✅ Запущенные экземпляры бота не найдены")
            return 0
        
        logger.info(f"📋 Найдено {len(running_instances)} запущенных экземпляров:")
        for i, instance in enumerate(running_instances, 1):
            logger.info(f"   {i}. PID: {instance['pid']} | Команда: {instance['cmdline']}")
        
        # Если только просмотр списка
        if args.list:
            logger.info("\n💡 Для остановки всех процессов выполните:")
            logger.info("   python stop_all_bots.py")
            logger.info("   python stop_all_bots.py --force  # для принудительного завершения")
            return 0
        
        # Подтверждение остановки
        if not args.force:
            try:
                response = input(f"\n❓ Остановить все {len(running_instances)} процессов? [y/N]: ")
                if response.lower() not in ['y', 'yes', 'да', 'д']:
                    logger.info("❌ Операция отменена пользователем")
                    return 1
            except (KeyboardInterrupt, EOFError):
                logger.info("\n❌ Операция отменена")
                return 1
        
        # Останавливаем процессы
        logger.info(f"\n🛑 Останавливаем {len(running_instances)} экземпляров...")
        stopped_count = stop_all_instances(force=args.force)
        
        if stopped_count == len(running_instances):
            logger.info("✅ Все экземпляры бота успешно остановлены")
            return 0
        else:
            logger.warning(f"⚠️ Удалось остановить только {stopped_count} из {len(running_instances)} процессов")
            return 1
            
    except ImportError:
        logger.error("❌ Не удалось импортировать process_lock модуль")
        logger.error("Убедитесь, что вы находитесь в директории проекта")
        return 1
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Операция прервана пользователем")
        sys.exit(1)
