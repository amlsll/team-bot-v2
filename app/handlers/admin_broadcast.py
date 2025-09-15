"""
Админская команда /adm_broadcast для рассылки сообщений.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from ..services.acl import require_admin
from ..services.notify import NotificationService

router = Router()


@router.message(Command("adm_broadcast"))
@require_admin
async def cmd_adm_broadcast(message: Message):
    """Админская команда для рассылки сообщений."""
    # Извлекаем текст сообщения
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Использование: /adm_broadcast <текст сообщения>")
        return
    
    broadcast_text = args[1]
    
    # Показываем кнопки выбора аудитории
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Ожидающим", callback_data=f"broadcast_waiting:{len(broadcast_text)}"),
            InlineKeyboardButton(text="В командах", callback_data=f"broadcast_teams:{len(broadcast_text)}")
        ]
    ])
    
    # Сохраняем текст в callback_data через длину (это упрощение)
    # В реальном проекте лучше использовать временное хранилище
    setattr(message, '_broadcast_text', broadcast_text)
    
    response = f"📢 **Рассылка сообщения:**\n\n{broadcast_text}\n\n**Выберите аудиторию:**"
    await message.reply(response, reply_markup=keyboard)


@router.callback_query(F.data.startswith("broadcast_waiting:"))
async def callback_broadcast_waiting(callback: CallbackQuery):
    """Обработчик рассылки ожидающим в очереди."""
    # Извлекаем текст из исходного сообщения между "📢 **Рассылка сообщения:**" и "**Выберите аудиторию:**"
    if callback.message and "📢 **Рассылка сообщения:**" in callback.message.text:
        text = callback.message.text
        start_marker = "📢 **Рассылка сообщения:**\n\n"
        end_marker = "\n\n**Выберите аудиторию:**"
        
        start_idx = text.find(start_marker)
        end_idx = text.find(end_marker)
        
        if start_idx != -1 and end_idx != -1:
            broadcast_text = text[start_idx + len(start_marker):end_idx]
        else:
            await callback.answer("Ошибка: не удалось извлечь текст сообщения.")
            return
    else:
        await callback.answer("Ошибка: исходное сообщение не найдено.")
        return
    
    notify_service = NotificationService(callback.bot)
    sent_count = await notify_service.broadcast_to_waiting(broadcast_text)
    
    await callback.message.edit_text(
        f"✅ Сообщение разослано ожидающим в очереди.\n📤 Доставлено: {sent_count}"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_teams:"))
async def callback_broadcast_teams(callback: CallbackQuery):
    """Обработчик рассылки участникам команд."""
    # Извлекаем текст из исходного сообщения между "📢 **Рассылка сообщения:**" и "**Выберите аудиторию:**"
    if callback.message and "📢 **Рассылка сообщения:**" in callback.message.text:
        text = callback.message.text
        start_marker = "📢 **Рассылка сообщения:**\n\n"
        end_marker = "\n\n**Выберите аудиторию:**"
        
        start_idx = text.find(start_marker)
        end_idx = text.find(end_marker)
        
        if start_idx != -1 and end_idx != -1:
            broadcast_text = text[start_idx + len(start_marker):end_idx]
        else:
            await callback.answer("Ошибка: не удалось извлечь текст сообщения.")
            return
    else:
        await callback.answer("Ошибка: исходное сообщение не найдено.")
        return
    
    notify_service = NotificationService(callback.bot)
    sent_count = await notify_service.broadcast_to_teams(broadcast_text)
    
    await callback.message.edit_text(
        f"✅ Сообщение разослано участникам команд.\n📤 Доставлено: {sent_count}"
    )
    await callback.answer()
