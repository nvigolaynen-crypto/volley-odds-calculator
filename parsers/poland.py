import pandas as pd
from .base_parser import BaseParser

class PolandParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """Заглушка – реальный парсинг Польши будет добавлен позже"""
        return pd.DataFrame(), pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Личные встречи для Польши вводятся вручную"""
        print("[DEBUG] Личные встречи для Польши вводятся вручную")
        return pd.DataFrame()
