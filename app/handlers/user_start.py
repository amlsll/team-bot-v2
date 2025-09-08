"""
Обработчики команды /start и процесса регистрации.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..services.storage import Storage

logger = logging.getLogger(__name__)

router = Router()

class RegistrationStates(StatesGroup):
    waiting_full_name = State()
    waiting_telegram_link = State()

class QuestionStates(StatesGroup):
    waiting_question = State()


# Константы для текстов
WELCOME_TEXT = """Привет!

Если ты еще не нашел команду для участия в конкурсе «Доброе Сердце Столицы» в номинации «Сообщество», то предлагаем тебе объединиться с волонтерами со всего города."""

SECOND_SCREEN_TEXT = """Нажми на кнопку «Присоединиться», чтобы попасть лист ожидания. Каждые 2 дня в 12:00 бот объединяет участников в команды и отправляет список участников, с которыми нужно связаться для подачи заявки.

Предлагаем после получения списка команды создать общий чат для удобства взаимодействия."""

REGISTRATION_START_TEXT = """Для участия в конкурсе нужно заполнить данные.

Введи свои Имя и Фамилию:"""

TELEGRAM_LINK_TEXT = """Теперь введи ссылку на свой Telegram:

Например: @username или https://t.me/username"""

JOIN_SUCCESS_TEXT = """В ожидании сейчас {queue_count} человек.

Ближайшее объединение в команды произойдет {next_match_time}"""

QUESTION_INFO_TEXT = """Если у тебя возникли вопросы, позвони по телефону горячей линии конкурса: +7 (499) 722⁠-69⁠-99 или напиши сообщение организаторам конкурса."""

QUESTION_PROMPT_TEXT = """Напиши свой вопрос организаторам конкурса:"""

QUESTION_SENT_TEXT = """Ваш вопрос отправлен организаторам. Ожидайте ответ в этом чате."""


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    if not message.from_user:
        logger.warning("Ополучена команда /start без информации о пользователе")
        return
    
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"🚀 Команда /start от пользователя {tg_id} (@{username})")
    
    try:
        # Очищаем состояние FSM на всякий случай
        await state.clear()
        
        storage = Storage()
        user = storage.get_user(tg_id)
        logger.debug(f"Пользователь {tg_id}: {user}")
    except Exception as e:
        logger.error(f"Ошибка при обработке /start для {tg_id}: {e}")
        await message.reply("Произошла ошибка. Попробуйте позже.")
        return
    
    try:
        # Если пользователь уже зарегистрирован и находится в очереди или команде
        if user and user.get('full_name') and user.get('telegram_link'):
            logger.info(f"Пользователь {tg_id} уже зарегистрирован, статус: {user.get('status')}")
            
            if user['status'] == 'waiting':
                # Проверяем, действительно ли пользователь в очереди
                in_queue = storage.get_queue_position(tg_id) != -1
                
                if in_queue:
                    # Пользователь в очереди - показываем экран ожидания
                    queue_count = len(storage.load()['queue'])
                    next_match_time = get_next_match_time()
                    text = JOIN_SUCCESS_TEXT.format(
                        queue_count=queue_count,
                        next_match_time=next_match_time
                    )
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Проверить статус ожидания", callback_data="status")],
                        [InlineKeyboardButton(text="Выйти из ожидания объединения", callback_data="leave")],
                        [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
                    ])
                    await message.answer(text, reply_markup=keyboard)
                    return
                else:
                    # Пользователь зарегистрирован, но не в очереди - показываем экран с возможностью присоединиться
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Присоединиться", callback_data="start_registration")],
                        [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
                    ])
                    await message.answer(SECOND_SCREEN_TEXT, reply_markup=keyboard)
                    return
            elif user['status'] == 'teamed':
                await message.answer("Ты уже состоишь в команде! Используй /status для просмотра информации о команде.")
                return
        
        # Показываем приветственный экран
        logger.info(f"Показываем приветственный экран пользователю {tg_id}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Запустить бота", callback_data="start_bot")],
            [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
        ])
        await message.answer(WELCOME_TEXT, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка в основной логике /start для {tg_id}: {e}")
        try:
            await message.reply("Произошла ошибка. Попробуйте ещё раз.")
        except:
            logger.error(f"Не удалось отправить сообщение об ошибке пользователю {tg_id}")


@router.callback_query(F.data == "start_bot")
async def callback_start_bot(callback: CallbackQuery):
    """Обработчик кнопки 'Запустить бота' - переход ко второму экрану."""
    if not callback.from_user:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Присоединиться", callback_data="start_registration")],
        [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
    ])
    await callback.message.edit_text(SECOND_SCREEN_TEXT, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "start_registration")
async def callback_start_registration(callback: CallbackQuery, state: FSMContext):
    """Начинаем процесс регистрации или добавляем в очередь уже зарегистрированного пользователя."""
    if not callback.from_user:
        return
    
    storage = Storage()
    tg_id = callback.from_user.id
    user = storage.get_user(tg_id)
    
    # Если пользователь уже зарегистрирован, сразу добавляем в очередь
    if user and user.get('full_name') and user.get('telegram_link'):
        # Обновляем статус на waiting и добавляем в очередь
        storage.set_user_status(tg_id, 'waiting', None)
        storage.enqueue(tg_id)
        
        # Показываем экран успешного присоединения
        queue_count = len(storage.load()['queue'])
        next_match_time = get_next_match_time()
        
        text = JOIN_SUCCESS_TEXT.format(
            queue_count=queue_count,
            next_match_time=next_match_time
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Проверить статус ожидания", callback_data="status")],
            [InlineKeyboardButton(text="Выйти из ожидания объединения", callback_data="leave")],
            [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("Добро пожаловать обратно в очередь! 👋")
        return
    
    # Пользователь не зарегистрирован, начинаем процесс регистрации
    await state.set_state(RegistrationStates.waiting_full_name)
    await callback.message.edit_text(REGISTRATION_START_TEXT)
    await callback.answer()


@router.callback_query(F.data == "ask_question")
async def callback_ask_question(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'У меня есть вопрос'."""
    if not callback.from_user:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать вопрос", callback_data="write_question")],
        [InlineKeyboardButton(text="Назад", callback_data="go_back")]
    ])
    await callback.message.edit_text(QUESTION_INFO_TEXT, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "write_question")
async def callback_write_question(callback: CallbackQuery, state: FSMContext):
    """Начинаем ввод вопроса."""
    if not callback.from_user:
        return
    
    await state.set_state(QuestionStates.waiting_question)
    await callback.message.edit_text(QUESTION_PROMPT_TEXT)
    await callback.answer()


@router.callback_query(F.data == "go_back")
async def callback_go_back(callback: CallbackQuery, state: FSMContext):
    """Возврат к предыдущему экрану."""
    if not callback.from_user:
        return
    
    # Создаем новое сообщение для возврата к началу
    # Вместо изменения frozen объекта, вызываем логику напрямую
    try:
        tg_id = callback.from_user.id
        username = callback.from_user.username or "unknown"
        logger.info(f"🔙 Возврат к началу от пользователя {tg_id} (@{username})")
        
        await state.clear()
        
        storage = Storage()
        user = storage.get_user(tg_id)
        
        # Если пользователь уже зарегистрирован
        if user and user.get('full_name') and user.get('telegram_link'):
            if user['status'] == 'waiting':
                queue_count = len(storage.load()['queue'])
                next_match_time = get_next_match_time()
                text = JOIN_SUCCESS_TEXT.format(
                    queue_count=queue_count,
                    next_match_time=next_match_time
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Проверить статус ожидания", callback_data="status")],
                    [InlineKeyboardButton(text="Выйти из ожидания объединения", callback_data="leave")],
                    [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
                ])
                await callback.message.edit_text(text, reply_markup=keyboard)
                await callback.answer()
                return
            elif user['status'] == 'teamed':
                await callback.message.edit_text("Ты уже состоишь в команде! Используй /status для просмотра информации о команде.")
                await callback.answer()
                return
        
        # Показываем приветственный экран
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Запустить бота", callback_data="start_bot")],
            [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
        ])
        await callback.message.edit_text(WELCOME_TEXT, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при возврате к началу для {tg_id}: {e}")
        await callback.answer("Произошла ошибка. Попробуйте /start", show_alert=True)


@router.message(QuestionStates.waiting_question)
async def process_question(message: Message, state: FSMContext):
    """Обработка ввода вопроса."""
    if not message.text or not message.from_user:
        await message.reply("Пожалуйста, введи вопрос текстом.")
        return
    
    storage = Storage()
    question_id = storage.create_question(
        user_id=message.from_user.id,
        username=message.from_user.username,
        text=message.text
    )
    
    # Уведомляем администраторов о новом вопросе
    await notify_admins_about_question(message.bot, question_id, message.from_user, message.text)
    
    await state.clear()
    await message.reply(QUESTION_SENT_TEXT)


@router.message(RegistrationStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ввода имени и фамилии."""
    if not message.text:
        await message.reply("Пожалуйста, введи свои Имя и Фамилию текстом.")
        return
    
    # Проверяем, что введено хотя бы два слова
    name_parts = message.text.strip().split()
    if len(name_parts) < 2:
        await message.reply("Пожалуйста, введи и Имя, и Фамилию (два слова минимум).")
        return
    
    await state.update_data(full_name=message.text.strip())
    await state.set_state(RegistrationStates.waiting_telegram_link)
    await message.reply(TELEGRAM_LINK_TEXT)


@router.message(RegistrationStates.waiting_telegram_link)
async def process_telegram_link(message: Message, state: FSMContext):
    """Обработка ввода ссылки на Telegram."""
    if not message.text:
        await message.reply("Пожалуйста, введи ссылку на свой Telegram.")
        return
    
    telegram_link = message.text.strip()
    
    # Простая валидация
    if not (telegram_link.startswith('@') or 'telegram' in telegram_link or 't.me' in telegram_link):
        await message.reply("Пожалуйста, введи корректную ссылку на Telegram (например: @username или https://t.me/username)")
        return
    
    # Получаем сохраненные данные
    data = await state.get_data()
    full_name = data.get('full_name')
    
    # Показываем данные для подтверждения
    confirmation_text = f"""Проверь введенные данные:

Имя Фамилия: {full_name}
Ссылка на Telegram: {telegram_link}

Все верно?"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, присоединиться к команде", callback_data="confirm_registration"),
            InlineKeyboardButton(text="Исправить", callback_data="restart_registration")
        ]
    ])
    
    await state.update_data(telegram_link=telegram_link)
    await message.reply(confirmation_text, reply_markup=keyboard)


@router.callback_query(F.data == "confirm_registration")
async def callback_confirm_registration(callback: CallbackQuery, state: FSMContext):
    """Подтверждение регистрации и добавление в очередь."""
    if not callback.from_user:
        return
    
    data = await state.get_data()
    storage = Storage()
    tg_id = callback.from_user.id
    
    # Создаем/обновляем пользователя
    storage.update_user(
        tg_id=tg_id,
        username=callback.from_user.username,
        name=callback.from_user.full_name,
        full_name=data['full_name'],
        telegram_link=data['telegram_link'],
        status='waiting'
    )
    
    # Добавляем в очередь
    storage.enqueue(tg_id)
    
    # Получаем информацию для ответа
    queue_count = len(storage.load()['queue'])
    next_match_time = get_next_match_time()
    
    text = JOIN_SUCCESS_TEXT.format(
        queue_count=queue_count,
        next_match_time=next_match_time
    )
    
    await callback.message.edit_text(text)
    await callback.answer("Добро пожаловать в очередь! 👋")
    await state.clear()


@router.callback_query(F.data == "restart_registration")
async def callback_restart_registration(callback: CallbackQuery, state: FSMContext):
    """Перезапуск регистрации."""
    await state.set_state(RegistrationStates.waiting_full_name)
    await callback.message.edit_text(REGISTRATION_START_TEXT)
    await callback.answer()


def get_next_match_time() -> str:
    """Возвращает время следующего объединения команд."""
    from ..services.scheduler import MatchScheduler
    
    # Создаем временный экземпляр планировщика для получения времени
    # В продакшене можно было бы использовать синглтон или внедрение зависимостей
    scheduler = MatchScheduler(None)  # bot не нужен для вычисления времени
    return scheduler.get_next_match_time_str()


async def show_registered_user_start_screen(callback_or_message, tg_id: int):
    """
    Показывает стартовый экран для зарегистрированного пользователя.
    Может использоваться как после выхода из очереди, так и при повторном /start.
    """
    storage = Storage()
    user = storage.get_user(tg_id)
    
    if not user or not user.get('full_name') or not user.get('telegram_link'):
        # Пользователь не полностью зарегистрирован
        return False
    
    if user['status'] == 'waiting':
        # Проверяем, действительно ли пользователь в очереди
        in_queue = storage.get_queue_position(tg_id) != -1
        
        if in_queue:
            # Пользователь в очереди - показываем экран ожидания
            queue_count = len(storage.load()['queue'])
            next_match_time = get_next_match_time()
            text = JOIN_SUCCESS_TEXT.format(
                queue_count=queue_count,
                next_match_time=next_match_time
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Проверить статус ожидания", callback_data="status")],
                [InlineKeyboardButton(text="Выйти из ожидания объединения", callback_data="leave")],
                [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
            ])
            await callback_or_message.edit_text(text, reply_markup=keyboard)
        else:
            # Пользователь зарегистрирован, но не в очереди - показываем возможность присоединиться
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Присоединиться", callback_data="start_registration")],
                [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
            ])
            await callback_or_message.edit_text(SECOND_SCREEN_TEXT, reply_markup=keyboard)
    elif user['status'] == 'teamed':
        # Пользователь уже в команде
        await callback_or_message.edit_text("Ты уже состоишь в команде! Используй /status для просмотра информации о команде.")
    else:
        # Пользователь зарегистрирован, но не в очереди - показываем возможность присоединиться
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Присоединиться", callback_data="start_registration")],
            [InlineKeyboardButton(text="У меня есть вопрос", callback_data="ask_question")]
        ])
        await callback_or_message.edit_text(SECOND_SCREEN_TEXT, reply_markup=keyboard)
    
    return True


async def notify_admins_about_question(bot, question_id: str, user, question_text: str):
    """Уведомляет всех администраторов о новом вопросе."""
    storage = Storage()
    store = storage.load()
    
    user_mention = f"@{user.username}" if user.username else f"ID {user.id}"
    admin_text = f"📋 Новый вопрос от пользователя {user_mention}:\n\n{question_text}\n\n💬 Для ответа используй: /answer {question_id} <текст ответа>"
    
    for admin_id, is_admin in store['admins'].items():
        if is_admin:
            try:
                await bot.send_message(admin_id, admin_text)
            except Exception as e:
                # Игнорируем ошибки отправки (админ мог заблокировать бота)
                print(f"Не удалось отправить уведомление админу {admin_id}: {e}")


# Обработчики кнопок из основного интерфейса
@router.callback_query(F.data == "status")
async def callback_status(callback: CallbackQuery):
    """Обработчик кнопки 'Проверить статус ожидания'."""
    if not callback.from_user:
        return
    
    try:
        from .user_status import cmd_status
        # Создаем mock объект сообщения
        class MockMessage:
            def __init__(self, callback_query):
                self.from_user = callback_query.from_user
                self.chat = callback_query.message.chat
                self.message_id = callback_query.message.message_id
                self.bot = callback_query.bot
            
            async def reply(self, text, **kwargs):
                await self.bot.send_message(self.chat.id, text, **kwargs)
        
        mock_message = MockMessage(callback)
        await cmd_status(mock_message)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса: {e}")
        await callback.answer("Ошибка. Используйте /status", show_alert=True)


@router.callback_query(F.data == "leave")
async def callback_leave(callback: CallbackQuery):
    """Обработчик кнопки 'Выйти из ожидания объединения'."""
    if not callback.from_user:
        return
    
    try:
        storage = Storage()
        tg_id = callback.from_user.id
        
        user = storage.get_user(tg_id)
        if not user:
            await callback.message.edit_text("Ошибка: пользователь не найден.")
            await callback.answer()
            return
        
        # Проверяем, есть ли что покидать
        in_queue = storage.get_queue_position(tg_id) != -1
        in_team = user['status'] == 'teamed' and user.get('team_id')
        
        if not in_queue and not in_team:
            await callback.message.edit_text("Ты не в очереди и не в команде.")
            await callback.answer()
            return
        
        # Показываем подтверждение
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="leave_confirm"),
                InlineKeyboardButton(text="Нет", callback_data="leave_cancel")
            ]
        ])
        
        await callback.message.edit_text("Точно выйти?", reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при выходе из очереди: {e}")
        await callback.answer("Ошибка. Используйте /leave", show_alert=True)
