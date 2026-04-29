import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        detail_table = soup.find('table', class_='s-table--round')
        if not detail_table:
            raise ValueError("Не найдена таблица с детальными результатами матчей")

        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                     'points_won': 0, 'points_lost': 0})

        rows = detail_table.find_all('tr', class_='table-game')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            home = cells[2].get_text(strip=True)
            away = cells[4].get_text(strip=True)

            total_score_span = row.find('span', class_='s-table__total-score')
            if not total_score_span:
                continue
            total_score = total_score_span.get_text(strip=True)
            sets_match = re.search(r'(\d+):(\d+)', total_score)
            if not sets_match:
                continue
            home_sets, away_sets = map(int, sets_match.groups())

            rounds_span = row.find('span', class_='s-table__rounds-score')
            if not rounds_span:
                continue
            rounds_text = rounds_span.get_text(strip=True)
            point_pairs = re.findall(r'(\d+):(\d+)', rounds_text)
            if not point_pairs:
                continue

            home_points = sum(int(p[0]) for p in point_pairs)
            away_points = sum(int(p[1]) for p in point_pairs)

            stats[home]['sets_won'] += home_sets
            stats[home]['sets_lost'] += away_sets
            stats[away]['sets_won'] += away_sets
            stats[away]['sets_lost'] += home_sets

            stats[home]['points_won'] += home_points
            stats[home]['points_lost'] += away_points
            stats[away]['points_won'] += away_points
            stats[away]['points_lost'] += home_points

        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()
