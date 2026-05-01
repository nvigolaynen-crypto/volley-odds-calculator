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
        team1_clean = clean(team1)
        team2_clean = clean(team2)
        print(f"[DEBUG] Поиск личных встреч: '{team1_clean}' vs '{team2_clean}' на {url}")

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки: {e}")
            return pd.DataFrame()

        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.find_all('tr', class_='table-game')
        if not rows:
            table = soup.find('table', class_='s-table--round')
            if table:
                rows = table.find_all('tr')[1:]
        if not rows:
            print("[DEBUG] Таблица матчей не найдена")
            return pd.DataFrame()

        print(f"[DEBUG] Найдено строк с матчами: {len(rows)}")
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
            home_clean = clean(home_raw)
            away_clean = clean(away_raw)

            if len(matches) < 5:
                print(f"[DEBUG] Пример: home='{home_clean}', away='{away_clean}', счёт='{total}'")

            if (home_clean == team1_clean and away_clean == team2_clean) or (home_clean == team2_clean and away_clean == team1_clean):
                matches.append({
                    'Дата': date,
                    'Хозяева': home_raw,
                    'Гости': away_raw,
                    'Счёт': total,
                    'Партии': ''
                })
        print(f"[DEBUG] Найдено личных встреч: {len(matches)}")
        return pd.DataFrame(matches)

    def _fetch_single_phase(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']]
