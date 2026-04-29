from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def fetch_stats(self, url: str):
        """Возвращает (df_stats, df_matches)"""
        pass
