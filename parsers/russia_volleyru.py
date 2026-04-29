import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table or 's-table--round' in matrix_table.get('class', []):
            raise ValueError("Не найдена таблица с результатами")
        
        stats, team_list = self._parse_matrix_table(matrix_table)
        df_sets = self._make_dataframe(stats, team_list)
        return df_sets, pd.DataFrame()  # второй DataFrame пока не используется

    def _parse_matrix_table(self, table):
        # Заголовки столбцов – номера команд
        thead = table.find('thead')
        header_row = thead.find('tr')
        ths = header_row.find_all('th')[2:]  # пропускаем первый пустой и "№"
        column_numbers = []
        for th in ths:
            text = th.get_text(strip=True)
            if text.isdigit():
                column_numbers.append(int(text))
        
        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        
        team_name_by_number = {}
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                    'points_won': 0, 'points_lost': 0})
        team_order = []  # сохраняем порядок команд
        
        # Проход по строкам для сбора названий, номеров и мячей
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            # Название команды (может быть внутри <a>)
            team_cell = cells[0]
            team_name = team_cell.get_text(strip=True)
            # Номер команды
            team_number = int(cells[1].get_text(strip=True))
            team_name_by_number[team_number] = team_name
            team_order.append(team_name)
            
            # Мячи из последнего td (data-balls)
            last_cell = cells[-1]
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                won, lost = map(int, balls.split(':'))
                stats[team_name]['points_won'] = won
                stats[team_name]['points_lost'] = lost
        
        # Проход для сбора сетов
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            home_num = int(cells[1].get_text(strip=True))
            home_name = team_name_by_number.get(home_num)
            if not home_name:
                continue
            
            # Ячейки результатов (начиная с 2-й, до последних 5)
            result_cells = cells[2:-5]  # после них идут "И", "В", "П", "Оч", "Пар"
            for col_idx, cell in enumerate(result_cells):
                if col_idx >= len(column_numbers):
                    break
                away_num = column_numbers[col_idx]
                away_name = team_name_by_number.get(away_num)
                if not away_name:
                    continue
                
                # В ячейке может быть один или два div (два матча)
                divs = cell.find_all('div')
                if not divs:
                    # Если div нет, возможно текст внутри td
                    text = cell.get_text(strip=True)
                    if text:
                        # Может быть несколько строк
                        for line in text.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            match = re.search(r'(\d+):(\d+)', line)
                            if match:
                                hs, aws = map(int, match.groups())
                                # Для первого и единственного матча определяем порядок:
                                # так как ячейка находится в строке home, то первый матч – home vs away
                                stats[home_name]['sets_won'] += hs
                                stats[home_name]['sets_lost'] += aws
                                stats[away_name]['sets_won'] += aws
                                stats[away_name]['sets_lost'] += hs
                    continue
                
                # Обрабатываем div'ы
                for idx, div in enumerate(divs):
                    score_text = div.get_text(strip=True)
                    match = re.search(r'(\d+):(\d+)', score_text)
                    if not match:
                        continue
                    hs, aws = map(int, match.groups())
                    # Чётный индекс – первый матч (home vs away), нечётный – второй (away vs home)
                    if idx % 2 == 0:
                        stats[home_name]['sets_won'] += hs
                        stats[home_name]['sets_lost'] += aws
                        stats[away_name]['sets_won'] += aws
                        stats[away_name]['sets_lost'] += hs
                    else:
                        stats[away_name]['sets_won'] += hs
                        stats[away_name]['sets_lost'] += aws
                        stats[home_name]['sets_won'] += aws
                        stats[home_name]['sets_lost'] += hs
        
        return stats, team_order

    def _make_dataframe(self, stats, team_order):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        # Сортируем в порядке, в котором команды идут в таблице (по убыванию выигранных сетов)
        df = df.set_index('Команда').loc[team_order].reset_index()
        return df[['Команда', 'Сеты', 'Мячи']]
