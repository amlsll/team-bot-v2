"""
Обработчики для автоматического обновления бота.
"""

import os
import json
import logging
from datetime import datetime
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiohttp import web
from aiohttp.web_request import Request

from ..services.acl import require_admin
from ..services.auto_update import AutoUpdateService

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("adm_update_check"))
@require_admin
async def cmd_check_updates(message: Message):
    """Админская команда для проверки наличия обновлений."""
    update_service = AutoUpdateService()
    
    try:
        has_updates, update_info = update_service.has_updates()
        
        if not has_updates:
            await message.reply("✅ Бот использует последнюю версию")
            return
        
        current = update_info.get('current', {})
        remote = update_info.get('remote', {})
        commits_behind = update_info.get('commits_behind', 0)
        
        response = f"""🔄 **Доступны обновления**

📍 **Текущая версия:**
• Коммит: `{current.get('short_hash', 'unknown')}`
• Дата: {current.get('date', 'unknown')[:19] if current.get('date') else 'unknown'}
• Сообщение: {current.get('message', 'unknown')[:50]}{'...' if len(current.get('message', '')) > 50 else ''}

🚀 **Новая версия:**
• Коммит: `{remote.get('short_hash', 'unknown')}`
• Дата: {remote.get('date', 'unknown')[:19] if remote.get('date') else 'unknown'}
• Сообщение: {remote.get('message', 'unknown')[:50]}{'...' if len(remote.get('message', '')) > 50 else ''}
• Автор: {remote.get('author', 'unknown')}

📊 **Статистика:** {commits_behind} новых коммитов

⚠️ **Для обновления используйте:** `/adm_update_apply`"""
        
        await message.reply(response)
        
    except Exception as e:
        logger.error(f"Ошибка проверки обновлений: {e}")
        await message.reply(f"❌ Ошибка при проверке обновлений: {e}")


@router.message(Command("adm_update_apply"))
@require_admin
async def cmd_apply_updates(message: Message):
    """Админская команда для применения обновлений."""
    update_service = AutoUpdateService()
    
    # Отправляем начальное сообщение
    status_message = await message.reply("🔄 Начинаем процесс обновления...")
    
    try:
        # Выполняем обновление
        result = await update_service.perform_full_update(force=False)
        
        if result['success']:
            # Формируем отчет об успешном обновлении
            response = "✅ **Обновление выполнено успешно!**\n\n"
            
            for step in result['steps']:
                step_name = step['step'].replace('_', ' ').title()
                status_emoji = "✅" if step['status'] == 'completed' else "❌"
                response += f"{status_emoji} {step_name}\n"
                
                if 'message' in step:
                    response += f"   {step['message'][:100]}{'...' if len(step['message']) > 100 else ''}\n"
                elif 'error' in step:
                    response += f"   ❌ {step['error'][:100]}{'...' if len(step['error']) > 100 else ''}\n"
            
            if result['restart_required']:
                response += "\n⚠️ **Требуется перезапуск бота для применения изменений**"
                response += "\n\nИспользуйте: `/adm_restart`"
            
            await status_message.edit_text(response)
            
        else:
            error_msg = result.get('error', 'Неизвестная ошибка')
            response = f"❌ **Обновление не удалось**\n\n{error_msg}\n\n"
            
            # Добавляем информацию о неудачных шагах
            for step in result['steps']:
                if step['status'] == 'failed':
                    step_name = step['step'].replace('_', ' ').title()
                    response += f"❌ {step_name}: {step.get('error', 'Unknown error')}\n"
            
            await status_message.edit_text(response)
            
    except Exception as e:
        logger.error(f"Критическая ошибка при обновлении: {e}")
        await status_message.edit_text(f"💥 Критическая ошибка: {e}")


@router.message(Command("adm_update_force"))
@require_admin  
async def cmd_force_update(message: Message):
    """Принудительное обновление без проверок."""
    update_service = AutoUpdateService()
    
    status_message = await message.reply("⚡ Принудительное обновление...")
    
    try:
        result = await update_service.perform_full_update(force=True)
        
        if result['success']:
            response = "✅ **Принудительное обновление завершено**\n\n"
            
            for step in result['steps']:
                step_name = step['step'].replace('_', ' ').title()
                status_emoji = "✅" if step['status'] == 'completed' else "❌"
                response += f"{status_emoji} {step_name}\n"
            
            if result['restart_required']:
                response += "\n⚠️ **Требуется перезапуск:** `/adm_restart`"
            
            await status_message.edit_text(response)
        else:
            await status_message.edit_text(f"❌ Принудительное обновление не удалось: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Ошибка принудительного обновления: {e}")
        await status_message.edit_text(f"💥 Ошибка: {e}")


@router.message(Command("adm_update_status"))
@require_admin
async def cmd_update_status(message: Message):
    """Показывает статус автообновления."""
    update_service = AutoUpdateService()
    
    try:
        current_info = update_service.get_current_commit_info()
        auto_update_enabled = update_service.auto_update_enabled
        
        response = f"""📊 **Статус автообновления**

🔧 **Автообновление:** {"✅ Включено" if auto_update_enabled else "❌ Отключено"}
🌿 **Ветка для обновлений:** {update_service.update_branch}
🔐 **GitHub webhook:** {"✅ Настроен" if update_service.github_secret else "❌ Не настроен"}

📍 **Текущая версия:**
• Коммит: `{current_info.get('short_hash', 'unknown')}`
• Дата: {current_info.get('date', 'unknown')[:19] if current_info.get('date') else 'unknown'}
• Сообщение: {current_info.get('message', 'unknown')[:60]}{'...' if len(current_info.get('message', '')) > 60 else ''}
• Автор: {current_info.get('author', 'unknown')}

🎛️ **Доступные команды:**
• `/adm_update_check` — проверить обновления
• `/adm_update_apply` — применить обновления  
• `/adm_update_force` — принудительное обновление
• `/adm_restart` — перезапуск бота"""
        
        await message.reply(response)
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        await message.reply(f"❌ Ошибка: {e}")


# Обработчик GitHub webhook (для использования с aiohttp)
async def github_webhook_handler(request: Request) -> web.Response:
    """Обработчик GitHub webhook для автоматического обновления."""
    update_service = AutoUpdateService()
    
    try:
        # Читаем тело запроса
        payload_body = await request.read()
        
        # Проверяем подпись (если настроена)
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not update_service.verify_github_signature(payload_body, signature):
            logger.warning("Неверная подпись GitHub webhook")
            return web.Response(status=401, text="Invalid signature")
        
        # Парсим JSON
        try:
            payload = json.loads(payload_body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Неверный JSON в GitHub webhook")
            return web.Response(status=400, text="Invalid JSON")
        
        # Парсим webhook данные
        webhook_data = update_service.parse_github_webhook(payload)
        if not webhook_data:
            logger.info("GitHub webhook не для нашей ветки или без коммитов")
            return web.Response(status=200, text="OK - ignored")
        
        logger.info(f"Получен GitHub webhook: {webhook_data['commits_count']} коммитов в {webhook_data['branch']}")
        
        # Проверяем, включено ли автообновление
        if not update_service.auto_update_enabled:
            logger.info("Автообновление отключено, игнорируем webhook")
            return web.Response(status=200, text="OK - auto-update disabled")
        
        # Запускаем обновление в фоне
        try:
            # В реальном приложении лучше использовать очередь задач
            import asyncio
            asyncio.create_task(handle_auto_update(update_service, webhook_data))
            
            return web.Response(status=200, text="OK - update started")
            
        except Exception as e:
            logger.error(f"Ошибка запуска автообновления: {e}")
            return web.Response(status=500, text=f"Error starting update: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки GitHub webhook: {e}")
        return web.Response(status=500, text=f"Error: {e}")


async def handle_auto_update(update_service: AutoUpdateService, webhook_data: dict):
    """Обрабатывает автоматическое обновление по webhook."""
    try:
        logger.info("Начинаем автоматическое обновление по GitHub webhook...")
        
        # Выполняем обновление
        result = await update_service.perform_full_update(force=False)
        
        if result['success']:
            logger.info("Автоматическое обновление выполнено успешно")
            
            # Можно отправить уведомление админам
            try:
                await notify_admins_about_update(webhook_data, result)
            except Exception as e:
                logger.error(f"Ошибка уведомления админов: {e}")
                
            # Если требуется перезапуск - запускаем его
            if result['restart_required']:
                logger.info("Планируем перезапуск бота через 5 секунд...")
                import asyncio
                await asyncio.sleep(5)
                await trigger_bot_restart()
                
        else:
            logger.error(f"Автоматическое обновление не удалось: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Критическая ошибка автообновления: {e}")


async def notify_admins_about_update(webhook_data: dict, result: dict):
    """Отправляет уведомление админам об автоматическом обновлении."""
    try:
        from ..bot import bot
        from ..services.storage import Storage
        
        storage = Storage()
        admins = storage.get_admins()
        
        if not admins:
            return
        
        commit = webhook_data['commit']
        message = f"""🔄 **Автоматическое обновление**

✅ Бот обновлен до новой версии

📝 **Новый коммит:**
• ID: `{commit['id'][:8]}`
• Автор: {commit['author']}
• Сообщение: {commit['message'][:60]}{'...' if len(commit['message']) > 60 else ''}

{"⚠️ Запланирован перезапуск бота" if result['restart_required'] else "ℹ️ Перезапуск не требуется"}"""
        
        for admin_id in admins:
            try:
                await bot.send_message(admin_id, message)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка уведомления админов: {e}")


async def trigger_bot_restart():
    """Запускает перезапуск бота."""
    try:
        # Создаем флаг-файл для сигнала о перезапуске
        restart_flag = os.path.join(os.path.dirname(__file__), '../../.restart_required')
        with open(restart_flag, 'w') as f:
            f.write(datetime.now().isoformat())
        
        logger.info("Создан флаг перезапуска")
        
        # Можно также отправить сигнал процессу
        import signal
        import os
        os.kill(os.getpid(), signal.SIGTERM)
        
    except Exception as e:
        logger.error(f"Ошибка запуска перезапуска: {e}")


# Функция для регистрации webhook endpoint в aiohttp приложении
def setup_github_webhook(app: web.Application, path: str = "/github-webhook"):
    """Регистрирует GitHub webhook endpoint."""
    app.router.add_post(path, github_webhook_handler)
    logger.info(f"GitHub webhook зарегистрирован на {path}")
