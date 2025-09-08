"""
Логика комплектования команд: база 5 + эластика +1/+2.
"""

from typing import List, Tuple


def match_round(queue: List[int], base: int = 5, elastic: int = 2) -> Tuple[List[List[int]], List[int]]:
    """
    Комплектует команды из очереди пользователей.
    
    Args:
        queue: Список ID пользователей в очереди (FIFO)
        base: Базовый размер команды (по умолчанию 5)
        elastic: Максимальное количество дополнительных участников (по умолчанию 2)
        
    Returns:
        Кортеж (команды, остаток_очереди)
        команды: список списков ID участников (первый в списке - капитан)
        остаток_очереди: участники, которые не вошли ни в одну команду
    """
    if not queue:
        return [], []
    
    # Создаем копию очереди для работы
    queue_copy = queue.copy()
    teams: List[List[int]] = []
    
    # Формируем полные команды базового размера
    i = 0
    while i + base <= len(queue_copy):
        teams.append(queue_copy[i:i + base])
        i += base
    
    # Остаток после формирования полных команд
    leftover = queue_copy[i:]
    
    # Эластичное распределение остатка по уже созданным командам
    j = 0
    while leftover and j < len(teams):
        # Добавляем участников в команды, не превышая base + elastic
        if len(teams[j]) < base + elastic:
            teams[j].append(leftover.pop(0))
        else:
            j += 1
    
    return teams, leftover


def validate_team_constraints(teams: List[List[int]], base: int = 5, elastic: int = 2) -> bool:
    """
    Проверяет, что все команды соответствуют ограничениям размера.
    
    Args:
        teams: Список команд
        base: Базовый размер команды
        elastic: Максимальное количество дополнительных участников
        
    Returns:
        True, если все команды валидны
    """
    for team in teams:
        if len(team) < base or len(team) > base + elastic:
            return False
    return True


def get_match_stats(queue_size: int, base: int = 5, elastic: int = 2) -> dict:
    """
    Возвращает статистику потенциального матчинга без его выполнения.
    
    Args:
        queue_size: Размер очереди
        base: Базовый размер команды
        elastic: Максимальное количество дополнительных участников
        
    Returns:
        Словарь со статистикой: teams_count, players_matched, players_remaining
    """
    if queue_size < base:
        return {
            'teams_count': 0,
            'players_matched': 0,
            'players_remaining': queue_size
        }
    
    # Симулируем матчинг для получения статистики
    dummy_queue = list(range(queue_size))
    teams, leftover = match_round(dummy_queue, base, elastic)
    
    return {
        'teams_count': len(teams),
        'players_matched': queue_size - len(leftover),
        'players_remaining': len(leftover)
    }
