"""
Административные команды для мониторинга и просмотра логов.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from ..services.acl import admin_required
from ..services.logger import get_logger, get_metrics
from ..services.health_monitor import health_monitor
from ..services.navigation import create_pagination_keyboard

logger = get_logger('admin_monitoring')
router = Router()


@router.message(Command("health"))
@admin_required
async def cmd_health_check(message: Message):
    """Показывает состояние здоровья бота."""
    try:
        # Запускаем проверки
        await health_monitor.run_all_checks()
        summary = health_monitor.get_health_summary()
        
        # Создаем текст отчета
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '❌',
            'unknown': '❓'
        }
        
        overall_emoji = status_emoji.get(summary['overall_status'], '❓')
        
        text = f"🏥 <b>Состояние здоровья бота</b>\n\n"
        text += f"{overall_emoji} <b>Общий статус:</b> {summary['overall_status'].upper()}\n"
        text += f"📊 <b>Проверок:</b> {summary['checks_count']}\n"
        text += f"✅ Здоровых: {summary['healthy_count']}\n"
        text += f"⚠️ Предупреждений: {summary['warning_count']}\n"
        text += f"❌ Критических: {summary['critical_count']}\n\n"
        
        text += "<b>Детали проверок:</b>\n"
        for name, check in summary['checks'].items():
            emoji = status_emoji.get(check['status'], '❓')
            text += f"{emoji} <code>{name}</code>: {check['message']}\n"
        
        # Добавляем кнопки для детального просмотра
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="health_refresh"),
                InlineKeyboardButton(text="📊 Метрики", callback_data="show_metrics")
            ],
            [
                InlineKeyboardButton(text="📋 Логи", callback_data="show_logs"),
                InlineKeyboardButton(text="🏠 Главная", callback_data="admin_menu")
            ]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке здоровья: {e}")
        await message.answer(f"❌ Ошибка при проверке здоровья: {str(e)}")


@router.callback_query(F.data == "health_refresh")
@admin_required
async def callback_health_refresh(callback: CallbackQuery):
    """Обновляет информацию о здоровье."""
    await callback.answer("🔄 Обновляем информацию...")
    
    try:
        await health_monitor.run_all_checks()
        summary = health_monitor.get_health_summary()
        
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '❌',
            'unknown': '❓'
        }
        
        overall_emoji = status_emoji.get(summary['overall_status'], '❓')
        
        text = f"🏥 <b>Состояние здоровья бота</b> (обновлено)\n\n"
        text += f"{overall_emoji} <b>Общий статус:</b> {summary['overall_status'].upper()}\n"
        text += f"📊 <b>Проверок:</b> {summary['checks_count']}\n"
        text += f"✅ Здоровых: {summary['healthy_count']}\n"
        text += f"⚠️ Предупреждений: {summary['warning_count']}\n"
        text += f"❌ Критических: {summary['critical_count']}\n\n"
        
        text += "<b>Детали проверок:</b>\n"
        for name, check in summary['checks'].items():
            emoji = status_emoji.get(check['status'], '❓')
            text += f"{emoji} <code>{name}</code>: {check['message']}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="health_refresh"),
                InlineKeyboardButton(text="📊 Метрики", callback_data="show_metrics")
            ],
            [
                InlineKeyboardButton(text="📋 Логи", callback_data="show_logs"),
                InlineKeyboardButton(text="🏠 Главная", callback_data="admin_menu")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении здоровья: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "show_metrics")
@admin_required
async def callback_show_metrics(callback: CallbackQuery):
    """Показывает метрики производительности."""
    await callback.answer()
    
    try:
        metrics = get_metrics()
        
        text = "📊 <b>Метрики производительности</b>\n\n"
        
        # Основные счетчики
        text += f"📩 <b>Сообщений обработано:</b> {metrics.get('messages_processed', 0)}\n"
        text += f"🔘 <b>Callback'ов обработано:</b> {metrics.get('callbacks_processed', 0)}\n"
        text += f"❌ <b>Ошибок:</b> {metrics.get('errors_count', 0)}\n"
        text += f"👥 <b>Активных пользователей:</b> {metrics.get('active_users_count', 0)}\n"
        
        # Время работы
        uptime_seconds = metrics.get('uptime_seconds', 0)
        uptime_str = str(timedelta(seconds=int(uptime_seconds)))
        text += f"⏱️ <b>Время работы:</b> {uptime_str}\n\n"
        
        # Последняя активность
        last_activity = metrics.get('last_activity', 0)
        if last_activity > 0:
            last_activity_dt = datetime.fromtimestamp(last_activity)
            text += f"🕐 <b>Последняя активность:</b> {last_activity_dt.strftime('%H:%M:%S')}\n\n"
        
        # Производительность обработчиков
        handlers_perf = metrics.get('handlers_performance', {})
        if handlers_perf:
            text += "<b>🚀 Производительность обработчиков:</b>\n"
            for handler, stats in sorted(handlers_perf.items(), key=lambda x: x[1]['avg_ms'], reverse=True)[:10]:
                avg_ms = stats['avg_ms']
                count = stats['count']
                emoji = "🐌" if avg_ms > 1000 else "⚡" if avg_ms < 100 else "🟡"
                text += f"{emoji} <code>{handler}</code>: {avg_ms:.1f}ms (×{count})\n"
        
        # Кнопки навигации
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="show_metrics"),
                InlineKeyboardButton(text="🏥 Здоровье", callback_data="health_refresh")
            ],
            [
                InlineKeyboardButton(text="📋 Логи", callback_data="show_logs"),
                InlineKeyboardButton(text="🏠 Главная", callback_data="admin_menu")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при показе метрик: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "show_logs")
@admin_required
async def callback_show_logs(callback: CallbackQuery):
    """Показывает последние логи."""
    await callback.answer()
    
    try:
        # Показываем список доступных файлов логов
        logs_dir = Path('logs')
        if not logs_dir.exists():
            await callback.answer("📋 Директория логов не найдена", show_alert=True)
            return
        
        log_files = sorted(logs_dir.glob('*.log*'), key=lambda x: x.stat().st_mtime, reverse=True)
        
        text = "📋 <b>Доступные файлы логов</b>\n\n"
        
        if not log_files:
            text += "Файлы логов не найдены"
        else:
            for i, log_file in enumerate(log_files[:10]):  # Показываем только последние 10
                file_stat = log_file.stat()
                size_mb = file_stat.st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(file_stat.st_mtime)
                text += f"📄 <code>{log_file.name}</code>\n"
                text += f"   💾 {size_mb:.1f}MB, изменен {modified.strftime('%H:%M:%S')}\n\n"
        
        # Кнопки для просмотра конкретных типов логов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Ошибки", callback_data="view_log_errors"),
                InlineKeyboardButton(text="📊 Метрики", callback_data="view_log_metrics")
            ],
            [
                InlineKeyboardButton(text="📝 Все логи", callback_data="view_log_all"),
                InlineKeyboardButton(text="🔄 Обновить", callback_data="show_logs")
            ],
            [
                InlineKeyboardButton(text="🏥 Здоровье", callback_data="health_refresh"),
                InlineKeyboardButton(text="🏠 Главная", callback_data="admin_menu")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при показе логов: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("view_log_"))
@admin_required
async def callback_view_log(callback: CallbackQuery):
    """Показывает содержимое лога."""
    await callback.answer()
    
    log_type = callback.data.split("_")[-1]
    
    try:
        logs_dir = Path('logs')
        log_file = None
        
        # Определяем файл лога по типу
        if log_type == "errors":
            log_file = logs_dir / "bot_errors.log"
        elif log_type == "metrics":
            log_file = logs_dir / "bot_performance.jsonl"
        elif log_type == "all":
            log_file = logs_dir / "bot_all.log"
        
        if not log_file or not log_file.exists():
            await callback.answer(f"Файл лога {log_type} не найден", show_alert=True)
            return
        
        # Читаем последние строки
        lines_to_read = 20
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-lines_to_read:] if len(lines) > lines_to_read else lines
        
        text = f"📋 <b>Последние записи: {log_file.name}</b>\n\n"
        
        if not last_lines:
            text += "Лог пуст"
        else:
            for line in last_lines:
                line = line.strip()
                if len(line) > 100:
                    line = line[:97] + "..."
                text += f"<code>{line}</code>\n"
        
        text += f"\n📊 Всего строк: {len(lines)}"
        
        # Кнопки навигации
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"view_log_{log_type}"),
                InlineKeyboardButton(text="📋 Все логи", callback_data="show_logs")
            ],
            [
                InlineKeyboardButton(text="🏠 Главная", callback_data="admin_menu")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре лога {log_type}: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(Command("metrics"))
@admin_required
async def cmd_metrics(message: Message):
    """Быстрый просмотр метрик."""
    try:
        metrics = get_metrics()
        
        text = "📊 <b>Быстрые метрики</b>\n\n"
        text += f"📩 Сообщений: {metrics.get('messages_processed', 0)}\n"
        text += f"🔘 Callback'ов: {metrics.get('callbacks_processed', 0)}\n"
        text += f"❌ Ошибок: {metrics.get('errors_count', 0)}\n"
        text += f"👥 Активных пользователей: {metrics.get('active_users_count', 0)}\n"
        
        uptime_seconds = metrics.get('uptime_seconds', 0)
        if uptime_seconds > 0:
            uptime_str = str(timedelta(seconds=int(uptime_seconds)))
            text += f"⏱️ Время работы: {uptime_str}\n"
        
        error_rate = 0
        total_ops = metrics.get('messages_processed', 0) + metrics.get('callbacks_processed', 0)
        if total_ops > 0:
            error_rate = metrics.get('errors_count', 0) / total_ops
        text += f"📈 Частота ошибок: {error_rate:.1%}\n"
        
        await message.answer(text)
        
    except Exception as e:
        logger.error(f"Ошибка при показе метрик: {e}")
        await message.answer(f"❌ Ошибка при получении метрик: {str(e)}")


@router.message(Command("logs"))
@admin_required
async def cmd_logs(message: Message):
    """Показывает последние ошибки из логов."""
    try:
        logs_dir = Path('logs')
        error_log = logs_dir / "bot_errors.log"
        
        if not error_log.exists():
            await message.answer("📋 Файл ошибок не найден")
            return
        
        # Читаем последние 10 строк
        with open(error_log, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_errors = lines[-10:] if len(lines) > 10 else lines
        
        if not last_errors:
            text = "✅ Недавних ошибок не найдено"
        else:
            text = "📋 <b>Последние ошибки:</b>\n\n"
            for line in last_errors:
                line = line.strip()
                if len(line) > 150:
                    line = line[:147] + "..."
                text += f"<code>{line}</code>\n\n"
        
        await message.answer(text)
        
    except Exception as e:
        logger.error(f"Ошибка при чтении логов: {e}")
        await message.answer(f"❌ Ошибка при чтении логов: {str(e)}")


@router.message(Command("clear_logs"))
@admin_required
async def cmd_clear_logs(message: Message):
    """Очищает старые логи."""
    try:
        logs_dir = Path('logs')
        if not logs_dir.exists():
            await message.answer("📋 Директория логов не найдена")
            return
        
        # Находим файлы старше 7 дней
        cutoff_time = datetime.now() - timedelta(days=7)
        cutoff_timestamp = cutoff_time.timestamp()
        
        removed_count = 0
        freed_mb = 0
        
        for log_file in logs_dir.glob('*.log*'):
            if log_file.is_file() and log_file.stat().st_mtime < cutoff_timestamp:
                file_size = log_file.stat().st_size
                log_file.unlink()
                removed_count += 1
                freed_mb += file_size / (1024 * 1024)
        
        if removed_count > 0:
            text = f"🗑️ Удалено {removed_count} старых файлов логов\n"
            text += f"💾 Освобождено {freed_mb:.1f}MB места"
        else:
            text = "📋 Старых файлов логов для удаления не найдено"
        
        await message.answer(text)
        
    except Exception as e:
        logger.error(f"Ошибка при очистке логов: {e}")
        await message.answer(f"❌ Ошибка при очистке логов: {str(e)}")
