#!/usr/bin/env python3
"""
Скрипт для тестирования настроек окружения
"""

import os
import sys
from pathlib import Path

def test_environment():
    """Проверка настроек окружения"""
    
    print("🔍 Проверка окружения team-bot проекта")
    print("=" * 50)
    
    # Проверка Python
    print(f"Python версия: {sys.version}")
    print(f"Python путь: {sys.executable}")
    
    # Проверка виртуального окружения
    venv_path = os.environ.get('VIRTUAL_ENV')
    if venv_path:
        print(f"✅ Виртуальное окружение: {venv_path}")
    else:
        print("❌ Виртуальное окружение не активировано")
    
    # Проверка PYTHONPATH
    pythonpath = os.environ.get('PYTHONPATH')
    if pythonpath:
        print(f"✅ PYTHONPATH: {pythonpath}")
    else:
        print("❌ PYTHONPATH не установлен")
    
    # Проверка переменных окружения
    env_vars = [
        'DEBUG', 'ENV', 'SECRET_KEY', 'API_KEY', 
        'DATABASE_URL', 'LOG_LEVEL', 'TIMEZONE', 'LANGUAGE'
    ]
    
    print("\n📋 Переменные окружения:")
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Скрываем секретные ключи
            if 'KEY' in var and len(value) > 10:
                display_value = value[:4] + '*' * (len(value) - 8) + value[-4:]
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: не установлена")
    
    # Проверка файлов проекта
    print("\n📁 Файлы проекта:")
    project_files = ['.env', 'requirements.txt', 'load_env.sh', '.venv']
    for file in project_files:
        if Path(file).exists():
            print(f"✅ {file}: найден")
        else:
            print(f"❌ {file}: не найден")
    
    print("\n🎉 Проверка завершена!")

if __name__ == "__main__":
    test_environment()
