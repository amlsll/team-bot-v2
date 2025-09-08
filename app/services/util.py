"""
Утилиты для работы с файлами и парсинга env.
"""

import os
import json
from typing import Any
from pathlib import Path


def atomic_write(file_path: str, data: Any) -> None:
    """
    Атомарная запись в JSON файл через временный файл.
    
    Args:
        file_path: Путь к целевому файлу
        data: Данные для записи
    """
    tmp_path = file_path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, file_path)
    except Exception as e:
        # Удаляем временный файл в случае ошибки
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise e


def ensure_file_exists(file_path: str, default_content: Any = None) -> None:
    """
    Убеждается, что файл существует. Если нет - создает с дефолтным содержимым.
    
    Args:
        file_path: Путь к файлу
        default_content: Содержимое по умолчанию
    """
    if not os.path.exists(file_path):
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        atomic_write(file_path, default_content or {})


def parse_int_list(value: str) -> list[int]:
    """
    Парсит строку с числами через запятую в список int.
    
    Args:
        value: Строка вида "123,456,789"
        
    Returns:
        Список чисел
    """
    if not value.strip():
        return []
    return [int(x.strip()) for x in value.split(',') if x.strip()]
