from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """
        Парсит турнирную таблицу.
        Возвращает (pandas.DataFrame, error_message)
        DataFrame должен содержать колонки: 'Команда', 'Сеты', 'Мячи'
        """
        pass

    def fetch_head_to_head(self, team1: str, team2: str):
        """
        Опционально: парсит историю личных встреч.
        По умолчанию возвращает None (не реализовано).
        """
        return None
