import pandas as pd
from .base_parser import BaseParser

class TurkeyParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """Заглушка – реальный парсинг Турции будет добавлен позже"""
        return pd.DataFrame(), pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Личные встречи для Турции вводятся вручную"""
        print("[DEBUG] Личные встречи для Турции вводятся вручную")
        return pd.DataFrame()
