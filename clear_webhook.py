#!/usr/bin/env python3
"""
Скрипт для принудительной очистки webhook.
"""

import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot

async def clear_webhook():
    load_dotenv()
    token = os.getenv('BOT_TOKEN')
    
    if not token:
        print("❌ BOT_TOKEN не найден")
        return
    
    bot = Bot(token=token)
    
    try:
        # Получаем информацию о webhook
        webhook_info = await bot.get_webhook_info()
        print(f"ℹ️ Текущий webhook: {webhook_info.url or 'не установлен'}")
        
        if webhook_info.url:
            print("🧹 Удаляем webhook...")
            await bot.delete_webhook(drop_pending_updates=True)
            print("✅ Webhook удален")
        else:
            print("ℹ️ Webhook уже не установлен")
        
        # Проверяем ещё раз
        webhook_info = await bot.get_webhook_info()
        print(f"✅ Проверка: {webhook_info.url or 'webhook очищен'}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(clear_webhook())
