import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str):
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table or 's-table--round' in matrix_table.get('class', []):
            raise ValueError("Не найдена матричная таблица на странице")
        
        stats = self._parse_matrix_table(matrix_table)
        df_sets = self._make_dataframe(stats)
        return df_sets, pd.DataFrame()

    def _parse_matrix_table(self, table):
        header_row = table.find('thead').find('tr')
        ths = header_row.find_all('th')[2:]
        column_numbers = []
        for th in ths:
            text = th.get_text(strip=True)
            if text.isdigit():
                column_numbers.append(int(text))
        
        team_name_by_number = {}
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                    'points_won': 0, 'points_lost': 0})
        
        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        
        # 1. Названия команд и общие очки из data-balls
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = cells[0].get_text(strip=True)
            team_number = int(cells[1].get_text(strip=True))
            team_name_by_number[team_number] = team_name
            
            last_cell = cells[-1]
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                won, lost = map(int, balls.split(':'))
                stats[team_name]['points_won'] = won
                stats[team_name]['points_lost'] = lost
        
        # 2. Сеты (оба круга)
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            home_num = int(cells[1].get_text(strip=True))
            home_name = team_name_by_number.get(home_num)
            if not home_name:
                continue
            
            for col_idx, cell in enumerate(cells[2:-5], start=2):
                if col_idx - 2 >= len(column_numbers):
                    break
                away_num = column_numbers[col_idx - 2]
                away_name = team_name_by_number.get(away_num)
                if not away_name:
                    continue
                
                divs = cell.find_all('div')
                # Первый матч: home vs away
                if len(divs) >= 1:
                    score_text = divs[0].get_text(strip=True)
                    match = re.search(r'(\d+):(\d+)', score_text)
                    if match:
                        hs, aws = map(int, match.groups())
                        stats[home_name]['sets_won'] += hs
                        stats[home_name]['sets_lost'] += aws
                        stats[away_name]['sets_won'] += aws
                        stats[away_name]['sets_lost'] += hs
                # Второй матч: away vs home
                if len(divs) >= 2:
                    score_text = divs[1].get_text(strip=True)
                    match = re.search(r'(\d+):(\d+)', score_text)
                    if match:
                        hs, aws = map(int, match.groups())
                        stats[away_name]['sets_won'] += hs
                        stats[away_name]['sets_lost'] += aws
                        stats[home_name]['sets_won'] += aws
                        stats[home_name]['sets_lost'] += hs
        return stats

    def _make_dataframe(self, stats):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']]