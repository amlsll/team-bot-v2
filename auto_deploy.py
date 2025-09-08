#!/usr/bin/env python3
"""
Скрипт автоматического деплоя с перезапуском бота.
Предназначен для запуска через systemd или supervisor.
"""

import os
import sys
import time
import signal
import logging
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('auto_deploy.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class AutoDeployService:
    """Сервис автоматического деплоя и перезапуска бота."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self.restart_flag = self.project_path / '.restart_required'
        self.shutdown_flag = self.project_path / '.shutdown_required'
        self.bot_process = None
        self.should_stop = False
        
        # Загружаем переменные окружения
        load_dotenv(self.project_path / '.env')
        
    def start_bot(self) -> subprocess.Popen:
        """Запускает процесс бота."""
        try:
            # Используем существующий надежный запуск
            cmd = [sys.executable, 'run_bot.py', '--skip-checks']
            
            logger.info(f"Запускаем бота: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"Бот запущен с PID: {process.pid}")
            return process
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
    
    def stop_bot(self, process: subprocess.Popen, timeout: int = 30) -> bool:
        """Останавливает процесс бота."""
        if not process or process.poll() is not None:
            return True
        
        try:
            logger.info(f"Останавливаем бот (PID: {process.pid})")
            
            # Сначала пробуем SIGTERM
            process.terminate()
            
            try:
                process.wait(timeout=timeout)
                logger.info("Бот остановлен корректно")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("Бот не ответил на SIGTERM, используем SIGKILL")
                process.kill()
                process.wait(timeout=5)
                logger.info("Бот принудительно остановлен")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {e}")
            return False
    
    def check_flags(self) -> str:
        """Проверяет флаги перезапуска/остановки."""
        if self.shutdown_flag.exists():
            return 'shutdown'
        elif self.restart_flag.exists():
            return 'restart'
        return 'none'
    
    def clear_flags(self):
        """Очищает флаги."""
        try:
            if self.restart_flag.exists():
                self.restart_flag.unlink()
            if self.shutdown_flag.exists():
                self.shutdown_flag.unlink()
        except Exception as e:
            logger.error(f"Ошибка очистки флагов: {e}")
    
    def monitor_bot(self, check_interval: int = 5):
        """Мониторинг и автоматический перезапуск бота."""
        logger.info("Запуск монитора автоматического деплоя")
        
        # Обработчики сигналов
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, останавливаем мониторинг...")
            self.should_stop = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Очищаем старые флаги
            self.clear_flags()
            
            # Запускаем бота
            self.bot_process = self.start_bot()
            
            while not self.should_stop:
                time.sleep(check_interval)
                
                # Проверяем состояние процесса
                if self.bot_process.poll() is not None:
                    # Бот упал
                    exit_code = self.bot_process.returncode
                    logger.error(f"Бот завершился с кодом {exit_code}")
                    
                    # Читаем последние строки вывода
                    try:
                        output = self.bot_process.stdout.read()
                        if output:
                            logger.error(f"Последний вывод: {output}")
                    except Exception:
                        pass
                    
                    # Проверяем флаги
                    flag_status = self.check_flags()
                    
                    if flag_status == 'shutdown':
                        logger.info("Обнаружен флаг остановки, завершаем мониторинг")
                        self.clear_flags()
                        break
                    elif flag_status == 'restart':
                        logger.info("Обнаружен флаг перезапуска")
                        self.clear_flags()
                    else:
                        logger.info("Неожиданное завершение, перезапускаем через 5 секунд...")
                        time.sleep(5)
                    
                    # Перезапускаем бота
                    self.bot_process = self.start_bot()
                
                else:
                    # Бот работает, проверяем флаги
                    flag_status = self.check_flags()
                    
                    if flag_status == 'shutdown':
                        logger.info("Получен запрос на остановку")
                        self.stop_bot(self.bot_process)
                        self.clear_flags()
                        break
                    elif flag_status == 'restart':
                        logger.info("Получен запрос на перезапуск")
                        self.stop_bot(self.bot_process)
                        self.clear_flags()
                        time.sleep(2)
                        self.bot_process = self.start_bot()
                        
        except KeyboardInterrupt:
            logger.info("Получено прерывание с клавиатуры")
        except Exception as e:
            logger.error(f"Критическая ошибка монитора: {e}")
        finally:
            # Останавливаем бота при завершении
            if self.bot_process:
                self.stop_bot(self.bot_process)
            logger.info("Мониторинг завершен")


def main():
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Автоматический деплой и мониторинг team-bot"
    )
    parser.add_argument(
        '--project-path', '-p',
        default='.',
        help='Путь к проекту (по умолчанию: текущая директория)'
    )
    parser.add_argument(
        '--check-interval', '-i',
        type=int,
        default=5,
        help='Интервал проверки в секундах (по умолчанию: 5)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Включить отладочный вывод'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        deploy_service = AutoDeployService(args.project_path)
        deploy_service.monitor_bot(args.check_interval)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
