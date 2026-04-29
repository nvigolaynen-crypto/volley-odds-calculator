from .base_parser import BaseParser
import pandas as pd

class ItalyParser(BaseParser):
    def fetch_stats(self, url: str):
        # TODO: реализовать парсинг для Италии
        return pd.DataFrame(), pd.DataFrame()