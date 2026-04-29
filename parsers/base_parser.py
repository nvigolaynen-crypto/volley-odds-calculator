from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def fetch_stats(self, url: str):
        """
        Парсит одну страницу (этап) и возвращает два DataFrame:
        - df_sets: колонки 'Команда', 'Сеты', 'Мячи'
        - df_matches: опционально (пока не используется)
        """
        pass