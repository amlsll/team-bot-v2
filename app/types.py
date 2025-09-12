"""
Модели данных для Telegram-бота комплектовщика команд.
"""

from typing import TypedDict, List, Dict, Literal, Optional

Status = Literal['waiting', 'teamed', 'registering', 'asking_question']


class User(TypedDict, total=False):
    """Модель пользователя."""
    tg_id: int
    username: Optional[str]  # username из Telegram
    name: Optional[str]      # автоматически из Telegram
    full_name: Optional[str] # введенное пользователем "Имя Фамилия"
    telegram_link: Optional[str]  # введенная пользователем ссылка на Telegram
    status: Status
    team_id: Optional[str]
    registration_step: Optional[str]  # для отслеживания этапа регистрации


class Team(TypedDict):
    """Модель команды."""
    id: str  # "C-12"
    members: List[int]  # порядок: 1-й — капитан
    created_at: str
    status: Literal['active', 'archived']


class Question(TypedDict):
    """Модель вопроса от пользователя."""
    id: str
    user_id: int
    username: Optional[str]
    text: str
    created_at: str
    answered: bool
    answer: Optional[str]
    answered_by: Optional[int]
    answered_at: Optional[str]


class Store(TypedDict):
    """Главная модель хранилища данных."""
    users: Dict[str, User]  # используем str(tg_id) как ключи
    queue: List[str]  # список строковых tg_id  
    teams: Dict[str, Team]
    counters: Dict[str, int]  # {"teamSeq": 0}
    admins: Dict[str, dict]  # строковые tg_id с метаданными
    questions: Dict[str, Question]  # вопросы от пользователей
    next_match_time: Optional[str]  # время следующего автоматического объединения
    user_messages: Optional[Dict[str, List[int]]]  # сообщения пользователей
    cache: Optional[Dict[str, str]]  # кэш для file_id и других данных
