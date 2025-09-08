"""
Система блокировки процессов для предотвращения запуска нескольких экземпляров бота.
"""

import os
import sys
import time
import psutil
import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ProcessLock:
    """Менеджер блокировки процессов для предотвращения дублирования."""
    
    def __init__(self, lock_name: str = "team_bot"):
        self.lock_name = lock_name
        self.lock_file = Path(tempfile.gettempdir()) / f"{lock_name}.lock"
        self.pid_file = Path(tempfile.gettempdir()) / f"{lock_name}.pid"
        self._locked = False
        self._current_pid = os.getpid()
    
    def is_process_running(self, pid: int) -> bool:
        """Проверяет, работает ли процесс с указанным PID."""
        try:
            process = psutil.Process(pid)
            # Проверяем, что это действительно наш процесс бота
            cmdline = ' '.join(process.cmdline())
            if any(keyword in cmdline.lower() for keyword in ['team_bot', 'start_bot', 'app.__main__', 'bot.py']):
                return process.is_running()
            return False
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    
    def get_running_instances(self) -> list:
        """Возвращает список PID запущенных экземпляров бота."""
        running_instances = []
        
        for process in psutil.process_iter(['pid', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(process.info['cmdline'])
                # Ищем процессы, связанные с нашим ботом
                if any(keyword in cmdline.lower() for keyword in ['team_bot', 'start_bot.py', 'app.__main__', '-m app']):
                    # Исключаем текущий процесс
                    if process.info['pid'] != self._current_pid:
                        running_instances.append({
                            'pid': process.info['pid'],
                            'cmdline': cmdline,
                            'start_time': process.info['create_time']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                continue
        
        return running_instances
    
    def acquire(self, timeout: int = 5) -> bool:
        """
        Получает блокировку процесса.
        
        Args:
            timeout: Максимальное время ожидания в секундах
            
        Returns:
            True если блокировка получена, False если не удалось
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Проверяем существующие блокировки
            if self.lock_file.exists():
                logger.info("Обнаружен существующий lock файл, проверяем...")
                
                try:
                    with open(self.lock_file, 'r') as f:
                        existing_pid = int(f.read().strip())
                    
                    # Проверяем, работает ли процесс
                    if self.is_process_running(existing_pid):
                        logger.warning(f"Обнаружен запущенный экземпляр бота (PID: {existing_pid})")
                        return False
                    else:
                        logger.info(f"Найден устаревший lock файл (PID: {existing_pid}), удаляем...")
                        self._cleanup_stale_lock()
                
                except (ValueError, FileNotFoundError, PermissionError) as e:
                    logger.warning(f"Ошибка при чтении lock файла: {e}, удаляем...")
                    self._cleanup_stale_lock()
            
            # Пытаемся создать новую блокировку
            try:
                self.lock_file.parent.mkdir(exist_ok=True)
                
                # Атомарное создание файла с PID
                with open(self.lock_file, 'w') as f:
                    f.write(str(self._current_pid))
                
                # Также создаем PID файл для мониторинга
                with open(self.pid_file, 'w') as f:
                    f.write(f"{self._current_pid}\n{time.time()}\n")
                
                self._locked = True
                logger.info(f"✅ Блокировка процесса получена (PID: {self._current_pid})")
                return True
                
            except (PermissionError, OSError) as e:
                logger.error(f"Не удалось создать lock файл: {e}")
                time.sleep(0.1)
        
        logger.error(f"Не удалось получить блокировку за {timeout} секунд")
        return False
    
    def release(self):
        """Освобождает блокировку процесса."""
        if not self._locked:
            return
        
        try:
            if self.lock_file.exists():
                # Проверяем, что это наш файл
                with open(self.lock_file, 'r') as f:
                    file_pid = int(f.read().strip())
                
                if file_pid == self._current_pid:
                    self.lock_file.unlink()
                    logger.info("✅ Блокировка процесса освобождена")
                else:
                    logger.warning(f"Lock файл принадлежит другому процессу (PID: {file_pid})")
            
            # Удаляем PID файл
            if self.pid_file.exists():
                self.pid_file.unlink()
                
        except (FileNotFoundError, PermissionError, ValueError) as e:
            logger.warning(f"Ошибка при освобождении блокировки: {e}")
        finally:
            self._locked = False
    
    def _cleanup_stale_lock(self):
        """Удаляет устаревшие lock файлы."""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
            if self.pid_file.exists():
                self.pid_file.unlink()
        except (FileNotFoundError, PermissionError):
            pass
    
    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            running_instances = self.get_running_instances()
            if running_instances:
                logger.error("\n❌ Обнаружены запущенные экземпляры бота:")
                for instance in running_instances:
                    logger.error(f"   PID: {instance['pid']} | Команда: {instance['cmdline']}")
                logger.error("\n🔧 Для остановки всех экземпляров выполните:")
                logger.error("   pkill -f 'team_bot|start_bot|python.*app'")
                logger.error("   или используйте: python stop_all_bots.py")
            
            raise RuntimeError("Не удалось получить блокировку: возможно уже запущен другой экземпляр бота")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


def check_running_instances() -> list:
    """Проверяет запущенные экземпляры бота без блокировки."""
    lock = ProcessLock()
    return lock.get_running_instances()


def stop_all_instances(force: bool = False) -> int:
    """
    Останавливает все запущенные экземпляры бота.
    
    Args:
        force: Если True, использует SIGKILL вместо SIGTERM
        
    Returns:
        Количество остановленных процессов
    """
    instances = check_running_instances()
    stopped_count = 0
    
    if not instances:
        logger.info("Запущенные экземпляры бота не найдены")
        return 0
    
    logger.info(f"Найдено {len(instances)} запущенных экземпляров, останавливаем...")
    
    for instance in instances:
        try:
            process = psutil.Process(instance['pid'])
            
            if force:
                process.kill()
                logger.info(f"💀 Принудительно завершен процесс PID: {instance['pid']}")
            else:
                process.terminate()
                logger.info(f"🛑 Отправлен сигнал завершения процессу PID: {instance['pid']}")
                
                # Ждем корректного завершения
                try:
                    process.wait(timeout=10)
                    logger.info(f"✅ Процесс PID: {instance['pid']} завершен корректно")
                except psutil.TimeoutExpired:
                    logger.warning(f"⏰ Процесс PID: {instance['pid']} не завершился, принудительно убиваем...")
                    process.kill()
            
            stopped_count += 1
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Не удалось остановить процесс PID: {instance['pid']} - {e}")
    
    # Очищаем все lock файлы
    lock = ProcessLock()
    lock._cleanup_stale_lock()
    
    logger.info(f"✅ Остановлено {stopped_count} экземпляров бота")
    return stopped_count
