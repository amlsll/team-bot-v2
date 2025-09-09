#!/usr/bin/env python3
"""
Полная очистка конфликтов Telegram API
"""
import os
import sys
import asyncio
import aiohttp
from pathlib import Path

async def clear_telegram_api():
    """Полностью очищает Telegram API от конфликтов"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ Нет токена бота")
        return False
    
    print("🧹 Очистка Telegram API...")
    
    async with aiohttp.ClientSession() as session:
        # 1. Удаляем webhook
        webhook_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
        params = {"drop_pending_updates": True}
        
        async with session.post(webhook_url, params=params) as resp:
            result = await resp.json()
            print(f"📡 Webhook удален: {'✅' if result.get('ok') else '❌'}")
        
        # 2. Очищаем все pending updates
        updates_url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {"offset": -1, "limit": 1}
        
        async with session.post(updates_url, params=params) as resp:
            result = await resp.json()
            if result.get('ok') and result.get('result'):
                last_update_id = result['result'][0]['update_id']
                # Подтверждаем все updates
                params = {"offset": last_update_id + 1}
                async with session.post(updates_url, params=params) as resp2:
                    print("🗑️ Pending updates очищены")
        
        print("✅ Telegram API полностью очищен")
        return True

if __name__ == "__main__":
    asyncio.run(clear_telegram_api())
