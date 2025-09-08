"""
Проверка прав доступа (ACL) для админских команд.
"""

import os
from functools import wraps
from typing import Callable, Any
from aiogram import types

from .storage import Storage
from .util import parse_int_list


def get_storage() -> Storage:
    """Получает экземпляр Storage."""
    return Storage()


def is_admin_by_env(tg_id: int) -> bool:
    """Проверяет, является ли пользователь админом согласно переменной окружения ADMINS."""
    admins_str = os.getenv('ADMINS', '')
    admin_ids = parse_int_list(admins_str)
    return tg_id in admin_ids


def is_admin(tg_id: int) -> bool:
    """
    Проверяет, является ли пользователь админом.
    Проверяет как белый список из env, так и runtime-права в storage.
    """
    # Проверяем белый список из env
    if is_admin_by_env(tg_id):
        return True
    
    # Проверяем runtime-права из storage
    storage = get_storage()
    return storage.is_admin(tg_id)


def require_admin(func: Callable) -> Callable:
    """
    Декоратор для проверки прав админа.
    Если пользователь не админ, отправляет сообщение об отказе.
    """
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs) -> Any:
        if not is_admin(message.from_user.id):
            await message.reply("Эта команда доступна только организаторам.")
            return
        return await func(message, *args, **kwargs)
    return wrapper


def verify_admin_code(code: str) -> bool:
    """Проверяет, совпадает ли код с ADMIN_CODE из env."""
    admin_code = os.getenv('ADMIN_CODE', '')
    return admin_code and code == admin_code
