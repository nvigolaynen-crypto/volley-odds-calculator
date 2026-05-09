import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class ItalyParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Ищем весь текст страницы
        page_text = soup.get_text()
        
        # Ищем секцию с данными о командах
        # Данные находятся после строки "Classifica Regular Season Serie A2 Credem Banca"
        match = re.search(r'Classifica Regular Season Serie A2 Credem Banca(.*?)Legenda', page_text, re.DOTALL)
        if not match:
            raise ValueError("Не удалось найти данные турнирной таблицы")
        
        table_text = match.group(1)
        
        # Разбиваем на строки
        lines = table_text.strip().split('\n')
        
        stats = {}
        # Регулярное выражение для поиска данных команды
        # Пример: "1 Abba Pineto | 58 | 26 | 20 | 6 | 10 | 6 | 4 | 2 | 2 | 2 | 66 | 32 | 2.273 | 2.089 | 2,06 | 1,09"
        pattern = re.compile(r'(\d+)\s+(.+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.,]+)\s*\|\s*([\d.,]+)\s*\|\s*([\d.,]+)\s*\|\s*([\d.,]+)')
        
        for line in lines:
            match = pattern.search(line)
            if match:
                team_name = match.group(2).strip()
                sets_won = int(match.group(12))  # Vinti
                sets_lost = int(match.group(13))  # Persi
                points_won = float(match.group(14).replace(',', '.'))  # Fatti
                points_lost = float(match.group(15).replace(',', '.'))  # Subiti
                
                stats[team_name] = {
                    'sets_won': sets_won,
                    'sets_lost': sets_lost,
                    'points_won': points_won,
                    'points_lost': points_lost
                }
        
        if not stats:
            raise ValueError("Не удалось извлечь данные о командах")
        
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        print("[DEBUG] Личные встречи для Италии вводятся вручную")
        return pd.DataFrame()

    def _make_dataframe(self, stats):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']]
