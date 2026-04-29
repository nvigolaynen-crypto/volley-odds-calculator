from .base_parser import BaseParser
import pandas as pd

class PolandParser(BaseParser):
    def fetch_stats(self, url: str):
        # TODO: реализовать парсинг для Польши
        return pd.DataFrame(), pd.DataFrame()