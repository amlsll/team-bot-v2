#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к Telegram Bot API.
"""

import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Загружаем переменные окружения
load_dotenv()

async def test_bot():
    """Тестирует подключение к боту."""
    token = os.getenv('BOT_TOKEN')
    if not token:
        print("❌ Токен не найден в .env")
        return
    
    print(f"✅ Токен загружен: {token[:10]}...")
    
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    try:
        # Получаем информацию о боте
        me = await bot.get_me()
        print(f"✅ Бот подключен успешно!")
        print(f"   Имя: {me.first_name}")
        print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        print(f"   Webhook: {webhook_info.url or 'не установлен'}")
        
    except Exception as e:
        print(f"❌ Ошибка подключения к боту: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_bot())

