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
        
        # Ищем таблицу по разным признакам
        table = soup.find('table', id='GareGiornata')
        if not table:
            table = soup.find('table', {'id': re.compile(r'GareGiornata', re.I)})
        if not table:
            # Ищем по классам
            table = soup.find('table', class_='GareGiornata')
        if not table:
            # Ищем любую таблицу, содержащую столбцы "Punti", "Partite", "Set"
            tables = soup.find_all('table')
            for tbl in tables:
                if tbl.find('th', string=re.compile(r'Punti|Partite|Set', re.I)):
                    table = tbl
                    break
        if not table:
            raise ValueError("Не найдена таблица с результатами")
        
        stats = {}
        rows = table.find_all('tr', id='EvenRow')
        if not rows:
            rows = table.find_all('tr')[2:]  # пропускаем заголовок
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 14:
                continue
            team_cell = cells[2].get_text(strip=True)
            # Убираем номер позиции (например, "1 " или "1.")
            team_name = re.sub(r'^\d+\.?\s*', '', team_cell).strip()
            sets_won = int(cells[10].get_text(strip=True))
            sets_lost = int(cells[11].get_text(strip=True))
            points_won = float(cells[12].get_text(strip=True).replace(',', '.'))
            points_lost = float(cells[13].get_text(strip=True).replace(',', '.'))
            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }
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
