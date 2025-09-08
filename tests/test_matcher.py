"""
Unit-тесты для модуля matcher.
"""

import pytest
from app.services.matcher import match_round, validate_team_constraints, get_match_stats


class TestMatchRound:
    """Тесты для функции match_round."""
    
    def test_empty_queue(self):
        """Тест с пустой очередью."""
        teams, leftover = match_round([])
        assert teams == []
        assert leftover == []
    
    def test_small_queue(self):
        """Тест с очередью меньше базового размера."""
        queue = [1, 2, 3, 4]  # 4 < 5
        teams, leftover = match_round(queue, base=5)
        assert teams == []
        assert leftover == [1, 2, 3, 4]
    
    def test_exact_base_size(self):
        """Тест с очередью точно равной базовому размеру (5*N)."""
        queue = list(range(1, 6))  # [1, 2, 3, 4, 5]
        teams, leftover = match_round(queue, base=5)
        assert len(teams) == 1
        assert teams[0] == [1, 2, 3, 4, 5]
        assert leftover == []
    
    def test_double_base_size(self):
        """Тест с очередью равной двум базовым размерам (5*N)."""
        queue = list(range(1, 11))  # [1, 2, ..., 10]
        teams, leftover = match_round(queue, base=5)
        assert len(teams) == 2
        assert teams[0] == [1, 2, 3, 4, 5]
        assert teams[1] == [6, 7, 8, 9, 10]
        assert leftover == []
    
    def test_base_plus_one(self):
        """Тест с очередью 5*N+1."""
        queue = list(range(1, 7))  # [1, 2, 3, 4, 5, 6]
        teams, leftover = match_round(queue, base=5, elastic=2)
        assert len(teams) == 1
        assert teams[0] == [1, 2, 3, 4, 5, 6]  # 5 + 1 эластик
        assert leftover == []
    
    def test_base_plus_two(self):
        """Тест с очередью 5*N+2."""
        queue = list(range(1, 8))  # [1, 2, 3, 4, 5, 6, 7]
        teams, leftover = match_round(queue, base=5, elastic=2)
        assert len(teams) == 1
        assert teams[0] == [1, 2, 3, 4, 5, 6, 7]  # 5 + 2 эластика
        assert leftover == []
    
    def test_base_plus_three(self):
        """Тест с очередью 5*N+3."""
        queue = list(range(1, 9))  # [1, 2, 3, 4, 5, 6, 7, 8]
        teams, leftover = match_round(queue, base=5, elastic=2)
        assert len(teams) == 1
        assert teams[0] == [1, 2, 3, 4, 5, 6, 7]  # 5 + 2 эластика
        assert leftover == [8]  # 1 остается
    
    def test_base_plus_four(self):
        """Тест с очередью 5*N+4."""
        queue = list(range(1, 10))  # [1, 2, 3, 4, 5, 6, 7, 8, 9]
        teams, leftover = match_round(queue, base=5, elastic=2)
        assert len(teams) == 1
        assert teams[0] == [1, 2, 3, 4, 5, 6, 7]  # 5 + 2 эластика
        assert leftover == [8, 9]  # 2 остается
    
    def test_multiple_teams_with_elastic(self):
        """Тест с несколькими командами и эластичным распределением."""
        queue = list(range(1, 13))  # [1, 2, ..., 12]
        teams, leftover = match_round(queue, base=5, elastic=2)
        assert len(teams) == 2
        assert teams[0] == [1, 2, 3, 4, 5, 11, 12]  # первая команда + 2 эластика (max)
        assert teams[1] == [6, 7, 8, 9, 10]  # вторая команда базовая
        assert leftover == []
    
    def test_custom_base_and_elastic(self):
        """Тест с кастомными значениями base и elastic."""
        queue = list(range(1, 8))  # [1, 2, 3, 4, 5, 6, 7]
        teams, leftover = match_round(queue, base=3, elastic=1)
        assert len(teams) == 2
        assert teams[0] == [1, 2, 3, 7]  # 3 + 1 эластик
        assert teams[1] == [4, 5, 6]     # точно 3
        assert leftover == []


class TestValidateTeamConstraints:
    """Тесты для функции validate_team_constraints."""
    
    def test_valid_teams(self):
        """Тест с валидными командами."""
        teams = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11]]
        assert validate_team_constraints(teams, base=5, elastic=2)
    
    def test_team_too_small(self):
        """Тест с командой меньше базового размера."""
        teams = [[1, 2, 3, 4], [6, 7, 8, 9, 10]]  # первая команда 4 < 5
        assert not validate_team_constraints(teams, base=5, elastic=2)
    
    def test_team_too_large(self):
        """Тест с командой больше базы + эластика."""
        teams = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11, 12, 13]]  # вторая команда 8 > 5+2
        assert not validate_team_constraints(teams, base=5, elastic=2)
    
    def test_empty_teams(self):
        """Тест с пустым списком команд."""
        assert validate_team_constraints([], base=5, elastic=2)


class TestGetMatchStats:
    """Тесты для функции get_match_stats."""
    
    def test_stats_empty_queue(self):
        """Тест статистики для пустой очереди."""
        stats = get_match_stats(0, base=5, elastic=2)
        assert stats == {
            'teams_count': 0,
            'players_matched': 0,
            'players_remaining': 0
        }
    
    def test_stats_small_queue(self):
        """Тест статистики для маленькой очереди."""
        stats = get_match_stats(4, base=5, elastic=2)
        assert stats == {
            'teams_count': 0,
            'players_matched': 0,
            'players_remaining': 4
        }
    
    def test_stats_exact_match(self):
        """Тест статистики для точного совпадения."""
        stats = get_match_stats(10, base=5, elastic=2)
        assert stats == {
            'teams_count': 2,
            'players_matched': 10,
            'players_remaining': 0
        }
    
    def test_stats_with_leftover(self):
        """Тест статистики с остатком."""
        stats = get_match_stats(13, base=5, elastic=2)
        assert stats['teams_count'] == 2
        assert stats['players_matched'] == 13  # все попадают в команды (5+3 и 5)
        assert stats['players_remaining'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
