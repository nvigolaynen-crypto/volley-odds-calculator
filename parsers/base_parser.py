from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def fetch_stats(self, url: str):
        pass
