from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """Возвращает (DataFrame, error_message) с колонками Команда, Сеты, Мячи"""
        pass

    def fetch_head_to_head(self, team1: str, team2: str):
        """Опционально: возвращает историю личных встреч (DataFrame). По умолчанию – None."""
        return None
