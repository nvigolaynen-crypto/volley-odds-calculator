from .base_parser import BaseParser
import pandas as pd

class TurkeyParser(BaseParser):
    def fetch_stats(self, url: str):
        # TODO: реализовать парсинг для Турции
        return pd.DataFrame(), pd.DataFrame()