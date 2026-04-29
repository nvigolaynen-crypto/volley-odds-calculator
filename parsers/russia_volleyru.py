import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Ищем матричную таблицу (без класса --round)
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table or 's-table--round' in matrix_table.get('class', []):
            raise ValueError("Не найдена матричная таблица с итоговой статистикой")

        stats = {}
        tbody = matrix_table.find('tbody')
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 2:
                continue

            # Название команды (первая ячейка, может содержать ссылку)
            team_cell = cells[0]
            team_name = team_cell.get_text(strip=True).split('(')[0].strip()

            # Последняя ячейка (колонка "Пар") содержит итоговые сеты, например "87:24"
            last_cell = cells[-1]
            sets_text = last_cell.get_text(strip=True)

            # Мячи из атрибута data-balls
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                points_won, points_lost = map(int, balls.split(':'))
            else:
                points_won = points_lost = 0

            if ':' in sets_text:
                sets_won, sets_lost = map(int, sets_text.split(':'))
            else:
                sets_won = sets_lost = 0

            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }

        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()
