"""
JSON-хранилище для данных бота с атомарной записью.
"""

import json
import os
from datetime import datetime
from typing import Optional, List
from threading import Lock

from ..types import Store, User, Team, Question
from .util import atomic_write, ensure_file_exists


class Storage:
    """Класс для работы с JSON-хранилищем данных."""
    
    def __init__(self, file_path: str = 'data.json'):
        self.file_path = file_path
        self._lock = Lock()
        self._ensure_initialized()
    
    def _ensure_initialized(self) -> None:
        """Инициализирует файл хранилища, если он не существует."""
        default_store: Store = {
            'users': {},
            'queue': [],
            'teams': {},
            'counters': {'teamSeq': 0},
            'admins': {},
            'questions': {}
        }
        ensure_file_exists(self.file_path, default_store)
    
    def load(self) -> Store:
        """Загружает данные из файла."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Если файл поврежден или отсутствует - возвращаем пустой store
            self._ensure_initialized()
            return self.load()
    
    def save(self, store: Store) -> None:
        """Сохраняет данные в файл атомарно."""
        with self._lock:
            atomic_write(self.file_path, store)
    
    def enqueue(self, tg_id: int) -> None:
        """Добавляет пользователя в очередь, если его там нет."""
        store = self.load()
        if tg_id not in store['queue']:
            store['queue'].append(tg_id)
            self.save(store)
    
    def remove_from_queue(self, tg_id: int) -> bool:
        """Удаляет пользователя из очереди. Возвращает True, если был удален."""
        store = self.load()
        if tg_id in store['queue']:
            store['queue'].remove(tg_id)
            self.save(store)
            return True
        return False
    
    def create_team(self, members: List[int]) -> str:
        """Создает новую команду. Возвращает ID команды."""
        store = self.load()
        
        # Генерируем новый ID команды
        team_seq = store['counters']['teamSeq']
        team_id = f"C-{team_seq + 1}"
        store['counters']['teamSeq'] = team_seq + 1
        
        # Создаем команду
        team: Team = {
            'id': team_id,
            'members': members,
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }
        store['teams'][team_id] = team
        
        self.save(store)
        return team_id
    
    def set_user_status(self, tg_id: int, status: str, team_id: Optional[str] = None) -> None:
        """Устанавливает статус пользователя."""
        store = self.load()
        
        tg_id_str = str(tg_id)
        if tg_id_str not in store['users']:
            store['users'][tg_id_str] = User(tg_id=tg_id, status='waiting')
        
        store['users'][tg_id_str]['status'] = status  # type: ignore
        store['users'][tg_id_str]['team_id'] = team_id
        
        self.save(store)
    
    def update_user(self, tg_id: int, **kwargs) -> None:
        """Обновляет данные пользователя."""
        store = self.load()
        
        tg_id_str = str(tg_id)
        if tg_id_str not in store['users']:
            store['users'][tg_id_str] = User(tg_id=tg_id, status='waiting')
        
        store['users'][tg_id_str].update(kwargs)
        self.save(store)
    
    def get_user(self, tg_id: int) -> Optional[User]:
        """Получает пользователя по ID."""
        store = self.load()
        return store['users'].get(str(tg_id))
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Получает команду по ID."""
        store = self.load()
        return store['teams'].get(team_id)
    
    def remove_from_team(self, team_id: str, tg_id: int) -> bool:
        """Удаляет пользователя из команды. Возвращает True, если был удален."""
        store = self.load()
        team = store['teams'].get(team_id)
        
        if team and tg_id in team['members']:
            team['members'].remove(tg_id)
            # Если команда опустела, архивируем её
            if not team['members']:
                team['status'] = 'archived'
            self.save(store)
            return True
        return False
    
    def get_queue_position(self, tg_id: int) -> int:
        """Возвращает позицию пользователя в очереди (0-based). -1 если не в очереди."""
        store = self.load()
        try:
            return store['queue'].index(tg_id)
        except ValueError:
            return -1
    
    def get_queue_size(self) -> int:
        """Возвращает размер очереди."""
        store = self.load()
        return len(store['queue'])
    
    def get_active_teams_count(self) -> int:
        """Возвращает количество активных команд."""
        store = self.load()
        return sum(1 for team in store['teams'].values() if team['status'] == 'active')
    
    def get_active_teams_avg_size(self) -> float:
        """Возвращает средний размер активных команд."""
        store = self.load()
        active_teams = [team for team in store['teams'].values() if team['status'] == 'active']
        if not active_teams:
            return 0.0
        return sum(len(team['members']) for team in active_teams) / len(active_teams)
    
    def is_admin(self, tg_id: int) -> bool:
        """Проверяет, является ли пользователь админом."""
        store = self.load()
        return store['admins'].get(tg_id, False)
    
    def set_admin(self, tg_id: int, is_admin: bool = True) -> None:
        """Устанавливает или снимает права админа."""
        store = self.load()
        store['admins'][tg_id] = is_admin
        self.save(store)
    
    def get_queue_usernames(self, limit: int = 10) -> List[str]:
        """Возвращает список username первых пользователей в очереди."""
        store = self.load()
        usernames = []
        for tg_id in store['queue'][:limit]:
            user = store['users'].get(tg_id)
            if user and user.get('username'):
                usernames.append(f"@{user['username']}")
            else:
                usernames.append(f"ID:{tg_id}")
        return usernames
    
    def create_question(self, user_id: int, username: Optional[str], text: str) -> str:
        """Создает новый вопрос. Возвращает ID вопроса."""
        store = self.load()
        
        # Генерируем новый ID вопроса
        question_seq = store['counters'].get('questionSeq', 0)
        question_id = f"Q-{question_seq + 1}"
        store['counters']['questionSeq'] = question_seq + 1
        
        # Создаем вопрос
        question: Question = {
            'id': question_id,
            'user_id': user_id,
            'username': username,
            'text': text,
            'created_at': datetime.now().isoformat(),
            'answered': False,
            'answer': None,
            'answered_by': None,
            'answered_at': None
        }
        store['questions'][question_id] = question
        
        self.save(store)
        return question_id
    
    def get_unanswered_questions(self) -> List[Question]:
        """Возвращает список неотвеченных вопросов."""
        store = self.load()
        return [q for q in store['questions'].values() if not q['answered']]
    
    def answer_question(self, question_id: str, answer: str, admin_id: int) -> bool:
        """Отвечает на вопрос. Возвращает True, если вопрос найден и отвечен."""
        store = self.load()
        question = store['questions'].get(question_id)
        
        if question and not question['answered']:
            question['answered'] = True
            question['answer'] = answer
            question['answered_by'] = admin_id
            question['answered_at'] = datetime.now().isoformat()
            self.save(store)
            return True
        return False
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """Получает вопрос по ID."""
        store = self.load()
        return store['questions'].get(question_id)
