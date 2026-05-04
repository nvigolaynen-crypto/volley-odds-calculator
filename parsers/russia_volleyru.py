import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        def clean(name):
            return name.split('(')[0].strip().lower()
        t1 = clean(team1)
        t2 = clean(team2)
        print(f"[DEBUG] Поиск личных встреч: '{t1}' vs '{t2}'")

        # Переход на страницу "Все игры"
        allgames_url = url.replace('predvaritelnyy', 'allgames')
        print(f"[DEBUG] Загружаем: {allgames_url}")

        resp = requests.get(allgames_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', class_='s-table--round')
        if not table:
            print("[DEBUG] Таблица s-table--round не найдена")
            return pd.DataFrame()

        rows = table.find_all('tr', class_='table-game')
        matches = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            date = cells[0].get_text(strip=True)
            home_raw = cells[2].get_text(strip=True)
            away_raw = cells[4].get_text(strip=True)
            score_span = row.find('span', class_='s-table__total-score')
            if not score_span:
                continue
            total = score_span.get_text(strip=True)
            home = clean(home_raw)
            away = clean(away_raw)
            if (home == t1 and away == t2) or (home == t2 and away == t1):
                matches.append({
                    'Дата': date,
                    'Хозяева': home_raw,
                    'Гости': away_raw,
                    'Счёт': total
                })
        print(f"[DEBUG] Найдено матчей: {len(matches)}")
        return pd.DataFrame(matches)

    def _fetch_single_phase(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table or 's-table--round' in matrix_table.get('class', []):
            raise ValueError("Не найдена матричная таблица")
        return self._parse_matrix_table(matrix_table)

    def _parse_matrix_table(self, table):
        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        stats = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = cells[0].get_text(strip=True).split('(')[0].strip()
            last_cell = cells[-1]
            sets_text = last_cell.get_text(strip=True)
            if ':' in sets_text:
                sw, sl = map(int, sets_text.split(':'))
            else:
                sw = sl = 0
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                pw, pl = map(int, balls.split(':'))
            else:
                pw = pl = 0
            stats[team_name] = {
                'sets_won': sw,
                'sets_lost': sl,
                'points_won': pw,
                'points_lost': pl
            }
        return stats

    def _make_dataframe(self, stats):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        return df.sort_values('sets_won', ascending=False)[['Команда', 'Сеты', 'Мячи']]
