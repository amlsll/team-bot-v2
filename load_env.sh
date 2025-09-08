#!/bin/bash

# Скрипт для загрузки переменных окружения

# Активация виртуального окружения
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Виртуальное окружение активировано"
else
    echo "❌ Виртуальное окружение не найдено. Создайте его командой: python3 -m venv .venv"
    exit 1
fi

# Загрузка переменных из .env файла
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    echo "✅ Переменные окружения загружены из .env"
else
    echo "❌ Файл .env не найден"
    exit 1
fi

# Проверка Python
python3 --version
echo "✅ Python готов к работе"

# Показать некоторые переменные окружения
echo ""
echo "Основные переменные окружения:"
echo "PYTHONPATH: $PYTHONPATH"
echo "ENV: $ENV"
echo "DEBUG: $DEBUG"
echo ""
echo "🚀 Окружение настроено и готово к работе!"

