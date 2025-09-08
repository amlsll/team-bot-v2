"""
Обработчики админских команд для работы с вопросами от пользователей.
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from ..services.storage import Storage
from ..services.acl import require_admin

router = Router()


@router.message(Command("answer"))
@require_admin
async def cmd_answer(message: Message):
    """Ответить на вопрос пользователя."""
    if not message.text:
        await message.reply("❌ Неверный формат. Используй: /answer <ID_вопроса> <текст_ответа>")
        return
    
    parts = message.text.split(' ', 2)
    if len(parts) < 3:
        await message.reply("❌ Неверный формат. Используй: /answer <ID_вопроса> <текст_ответа>")
        return
    
    question_id = parts[1]
    answer_text = parts[2]
    
    storage = Storage()
    question = storage.get_question(question_id)
    
    if not question:
        await message.reply(f"❌ Вопрос с ID {question_id} не найден.")
        return
    
    if question['answered']:
        await message.reply(f"❌ На вопрос {question_id} уже отвечено.")
        return
    
    # Сохраняем ответ
    success = storage.answer_question(question_id, answer_text, message.from_user.id)
    
    if success:
        # Отправляем ответ пользователю
        try:
            await message.bot.send_message(
                question['user_id'],
                f"💬 Сообщение от администратора:\n\n{answer_text}"
            )
            await message.reply(f"✅ Ответ отправлен пользователю на вопрос {question_id}")
        except Exception as e:
            await message.reply(f"❌ Ответ сохранен, но не удалось отправить пользователю: {e}")
    else:
        await message.reply(f"❌ Ошибка при сохранении ответа на вопрос {question_id}")


@router.message(Command("questions"))
@require_admin  
async def cmd_questions(message: Message):
    """Показать список неотвеченных вопросов."""
    storage = Storage()
    questions = storage.get_unanswered_questions()
    
    if not questions:
        await message.reply("📋 Нет неотвеченных вопросов.")
        return
    
    text = "📋 Неотвеченные вопросы:\n\n"
    for question in questions[:10]:  # Показываем максимум 10 вопросов
        user_mention = f"@{question['username']}" if question['username'] else f"ID {question['user_id']}"
        question_preview = question['text'][:100] + ("..." if len(question['text']) > 100 else "")
        text += f"🔹 {question['id']} от {user_mention}:\n{question_preview}\n\n"
    
    if len(questions) > 10:
        text += f"... и еще {len(questions) - 10} вопросов"
    
    await message.reply(text)


@router.message(Command("question"))
@require_admin
async def cmd_question_details(message: Message):
    """Показать подробности конкретного вопроса."""
    if not message.text:
        await message.reply("❌ Укажи ID вопроса. Используй: /question <ID_вопроса>")
        return
    
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        await message.reply("❌ Укажи ID вопроса. Используй: /question <ID_вопроса>")
        return
    
    question_id = parts[1]
    storage = Storage()
    question = storage.get_question(question_id)
    
    if not question:
        await message.reply(f"❌ Вопрос с ID {question_id} не найден.")
        return
    
    user_mention = f"@{question['username']}" if question['username'] else f"ID {question['user_id']}"
    status = "✅ Отвечено" if question['answered'] else "⏳ Ожидает ответа"
    
    text = f"📋 Вопрос {question['id']}\n\n"
    text += f"👤 От: {user_mention}\n"
    text += f"📅 Создан: {question['created_at']}\n"
    text += f"📝 Статус: {status}\n\n"
    text += f"❓ Вопрос:\n{question['text']}\n"
    
    if question['answered']:
        text += f"\n💬 Ответ:\n{question['answer']}\n"
        text += f"📅 Отвечено: {question['answered_at']}"
    else:
        text += f"\n💡 Для ответа используй: /answer {question_id} <текст_ответа>"
    
    await message.reply(text)
