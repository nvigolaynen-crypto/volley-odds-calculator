from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def fetch_stats(self, url: str, combine_phases: bool = False):
        pass

    @abstractmethod
    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        pass
