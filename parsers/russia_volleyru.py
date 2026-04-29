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
        
        # Ищем таблицу (обычно class="s-table", но может быть и без класса)
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table:
            # попробуем найти любую таблицу с результатами
            tables = soup.find_all('table')
            for tbl in tables:
                if 's-table--round' not in tbl.get('class', []) and tbl.find('tbody'):
                    matrix_table = tbl
                    break
        if not matrix_table:
            raise ValueError("Не найдена таблица с результатами")
        
        stats = self._parse_matrix_table(matrix_table)
        df_sets = self._make_dataframe(stats)
        return df_sets, pd.DataFrame()

    def _parse_matrix_table(self, table):
        # Получаем номера команд из заголовка
        header_row = table.find('thead').find('tr')
        if not header_row:
            raise ValueError("Нет заголовка таблицы")
        ths = header_row.find_all('th')[2:]  # первые два столбца - пустой и №
        column_numbers = []
        for th in ths:
            text = th.get_text(strip=True)
            if text.isdigit():
                column_numbers.append(int(text))
            else:
                # если не цифра, пробуем взять порядковый номер
                column_numbers.append(len(column_numbers)+1)
        
        team_name_by_number = {}
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                    'points_won': 0, 'points_lost': 0})
        
        tbody = table.find('tbody')
        if not tbody:
            raise ValueError("Нет тела таблицы")
        rows = tbody.find_all('tr')
        
        # Сначала собираем названия команд и мячи из последнего столбца
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = cells[0].get_text(strip=True)
            # Иногда в первой ячейке может быть ссылка, берем текст
            team_name = team_name.split('(')[0].strip()
            team_number = int(cells[1].get_text(strip=True))
            team_name_by_number[team_number] = team_name
            
            # Мячи: ищем в последней ячейке атрибут data-balls
            last_cell = cells[-1]
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                won, lost = map(int, balls.split(':'))
                stats[team_name]['points_won'] = won
                stats[team_name]['points_lost'] = lost
            else:
                # Если нет data-balls, пробуем извлечь из текста последней ячейки (формат "87:24")
                text_balls = last_cell.get_text(strip=True)
                if ':' in text_balls:
                    parts = text_balls.split(':')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        stats[team_name]['points_won'] = int(parts[0])
                        stats[team_name]['points_lost'] = int(parts[1])
        
        # Теперь собираем сеты из ячеек
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
                
                # В ячейке может быть один или два div (два матча)
                divs = cell.find_all('div')
                # Если div-ов нет, пробуем взять текст напрямую (может быть без div)
                if not divs:
                    text = cell.get_text(strip=True)
                    if text:
                        divs = [cell]  # обрабатываем как один элемент
                
                # Обрабатываем каждый div
                for idx, div in enumerate(divs):
                    score_text = div.get_text(strip=True)
                    match = re.search(r'(\d+)[:;—-](\d+)', score_text)
                    if not match:
                        continue
                    hs, aws = map(int, match.groups())
                    # Чётность индекса определяет, кто хозяин
                    if idx % 2 == 0:
                        # первый матч: home vs away
                        stats[home_name]['sets_won'] += hs
                        stats[home_name]['sets_lost'] += aws
                        stats[away_name]['sets_won'] += aws
                        stats[away_name]['sets_lost'] += hs
                    else:
                        # второй матч: away vs home
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
