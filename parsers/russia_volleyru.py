import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """
        Парсит один или несколько этапов (если combine_phases=True).
        Возвращает DataFrame с колонками: Команда, Сеты, Мячи
        """
        if combine_phases:
            stats = self._fetch_all_phases(url)
        else:
            stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def _fetch_single_phase(self, url: str):
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, 'html.parser')
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table:
            raise ValueError("Не найдена таблица с результатами")
        return self._parse_matrix_table(matrix_table)

    def _fetch_all_phases(self, start_url: str):
        resp = requests.get(start_url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, 'html.parser')
        tabs = soup.find_all('a', class_='vl-tabs__item')
        phase_urls = []
        for tab in tabs:
            href = tab.get('href')
            name = tab.get_text(strip=True)
            if href and name not in ['Все игры', 'Положение', 'Фотографии', 'Статистика']:
                full_url = urljoin(start_url, href)
                phase_urls.append(full_url)
        phase_urls = list(dict.fromkeys(phase_urls))  # убираем дубликаты

        combined_stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                              'points_won': 0, 'points_lost': 0})
        for phase_url in phase_urls:
            phase_stats = self._fetch_single_phase(phase_url)
            for team, data in phase_stats.items():
                combined_stats[team]['sets_won'] += data['sets_won']
                combined_stats[team]['sets_lost'] += data['sets_lost']
                combined_stats[team]['points_won'] += data['points_won']
                combined_stats[team]['points_lost'] += data['points_lost']
        return combined_stats

    def _parse_matrix_table(self, table):
        thead = table.find('thead')
        header_row = thead.find('tr')
        ths = header_row.find_all('th')[2:]
        column_numbers = [int(th.get_text(strip=True)) for th in ths if th.get_text(strip=True).isdigit()]

        team_by_num = {}
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})

        tbody = table.find('tbody')
        rows = tbody.find_all('tr')

        # Извлекаем названия команд и итоговые очки из data-balls
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = cells[0].get_text(strip=True)
            team_num = int(cells[1].get_text(strip=True))
            team_by_num[team_num] = team_name
            last_cell = cells[-1]
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                pw, pl = map(int, balls.split(':'))
                stats[team_name]['points_won'] = pw
                stats[team_name]['points_lost'] = pl

        # Извлекаем сеты из ячеек
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            home_num = int(cells[1].get_text(strip=True))
            home_name = team_by_num.get(home_num)
            if not home_name:
                continue
            result_cells = cells[2:-5]
            for col_idx, cell in enumerate(result_cells):
                if col_idx >= len(column_numbers):
                    break
                away_num = column_numbers[col_idx]
                away_name = team_by_num.get(away_num)
                if not away_name:
                    continue
                divs = cell.find_all('div')
                if len(divs) >= 1:
                    score = re.search(r'(\d+):(\d+)', divs[0].get_text())
                    if score:
                        hs, aws = map(int, score.groups())
                        stats[home_name]['sets_won'] += hs
                        stats[home_name]['sets_lost'] += aws
                        stats[away_name]['sets_won'] += aws
                        stats[away_name]['sets_lost'] += hs
                if len(divs) >= 2:
                    score = re.search(r'(\d+):(\d+)', divs[1].get_text())
                    if score:
                        hs, aws = map(int, score.groups())
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
