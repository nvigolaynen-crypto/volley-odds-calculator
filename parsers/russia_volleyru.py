import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        if combine_phases:
            stats = self._fetch_all_phases(url)
        else:
            stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def _fetch_single_phase(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Используем детальную таблицу матчей (s-table--round)
        matches_table = soup.find('table', class_='s-table--round')
        if not matches_table:
            raise ValueError("Не найдена таблица с детальными результатами матчей")
        
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})
        
        rows = matches_table.find_all('tr', class_='table-game')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            home = cells[2].get_text(strip=True)
            away = cells[4].get_text(strip=True)
            total_span = row.find('span', class_='s-table__total-score')
            if not total_span:
                continue
            total_text = total_span.get_text(strip=True)
            sets_match = re.search(r'(\d+):(\d+)', total_text)
            if not sets_match:
                continue
            home_sets, away_sets = map(int, sets_match.groups())
            stats[home]['sets_won'] += home_sets
            stats[home]['sets_lost'] += away_sets
            stats[away]['sets_won'] += away_sets
            stats[away]['sets_lost'] += home_sets
            
            rounds_span = row.find('span', class_='s-table__rounds-score')
            if rounds_span:
                rounds_text = rounds_span.get_text(strip=True)
                pairs = re.findall(r'(\d+):(\d+)', rounds_text)
                home_pts = sum(int(p[0]) for p in pairs)
                away_pts = sum(int(p[1]) for p in pairs)
                stats[home]['points_won'] += home_pts
                stats[home]['points_lost'] += away_pts
                stats[away]['points_won'] += away_pts
                stats[away]['points_lost'] += home_pts
        
        # Если очки не найдены, берём их из матричной таблицы (data-balls)
        if not any(v['points_won'] > 0 for v in stats.values()):
            matrix_table = soup.find('table', class_='s-table')
            if matrix_table and 's-table--round' not in matrix_table.get('class', []):
                points_data = self._extract_points_from_matrix(matrix_table)
                for team, (pw, pl) in points_data.items():
                    if team in stats:
                        stats[team]['points_won'] = pw
                        stats[team]['points_lost'] = pl
                    else:
                        stats[team] = {'sets_won': 0, 'sets_lost': 0, 'points_won': pw, 'points_lost': pl}
        return stats

    def _extract_points_from_matrix(self, matrix_table):
        points = {}
        tbody = matrix_table.find('tbody')
        for row in tbody.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team = cells[0].get_text(strip=True).split('(')[0].strip()
            last_cell = cells[-1]
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                pw, pl = map(int, balls.split(':'))
                points[team] = (pw, pl)
        return points

    def _fetch_all_phases(self, start_url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(start_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        tabs = soup.find_all('a', class_='vl-tabs__item')
        phase_urls = []
        for tab in tabs:
            href = tab.get('href')
            name = tab.get_text(strip=True)
            if href and name not in ['Все игры', 'Положение', 'Фотографии', 'Статистика']:
                phase_urls.append(urljoin(start_url, href))
        phase_urls = list(dict.fromkeys(phase_urls))
        combined = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})
        for phase_url in phase_urls:
            phase_stats = self._fetch_single_phase(phase_url)
            for team, data in phase_stats.items():
                combined[team]['sets_won'] += data['sets_won']
                combined[team]['sets_lost'] += data['sets_lost']
                combined[team]['points_won'] += data['points_won']
                combined[team]['points_lost'] += data['points_lost']
        return combined

    def _make_dataframe(self, stats):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']]
