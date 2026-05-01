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
        team1_norm = self._normalize_team_name(team1)
        team2_norm = self._normalize_team_name(team2)
        print(f"[DEBUG] Поиск личных встреч: '{team1_norm}' vs '{team2_norm}'")

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки: {e}")
            return pd.DataFrame()

        soup = BeautifulSoup(resp.text, 'html.parser')
        # Ищем таблицу с матчами (s-table--round)
        table = soup.find('table', class_='s-table--round')
        if not table:
            print("[DEBUG] Таблица s-table--round не найдена")
            return pd.DataFrame()

        rows = table.find_all('tr', class_='table-game')
        print(f"[DEBUG] Найдено строк: {len(rows)}")
        matches = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            date = cells[0].get_text(strip=True)
            home_raw = cells[2].get_text(strip=True)
            away_raw = cells[4].get_text(strip=True)
            home_norm = self._normalize_team_name(home_raw)
            away_norm = self._normalize_team_name(away_raw)
            # Ячейка со счётом – обычно последняя, но может быть предпоследняя
            score_span = row.find('span', class_='s-table__total-score')
            if not score_span:
                continue
            score = score_span.get_text(strip=True)  # например, "3:1"
            rounds_span = row.find('span', class_='s-table__rounds-score')
            rounds = rounds_span.get_text(strip=True) if rounds_span else ''
            # Сравниваем нормализованные названия
            if (home_norm == team1_norm and away_norm == team2_norm) or (home_norm == team2_norm and away_norm == team1_norm):
                matches.append({
                    'Дата': date,
                    'Хозяева': home_raw,
                    'Гости': away_raw,
                    'Счёт': score,
                    'Партии': rounds
                })
        print(f"[DEBUG] Найдено личных встреч: {len(matches)}")
        return pd.DataFrame(matches)

    def _normalize_team_name(self, name: str) -> str:
        # Убираем город в скобках, лишние пробелы, приводим к нижнему регистру
        name = name.split('(')[0].strip()
        name = re.sub(r'\s+', ' ', name)
        name = name.lower()
        # Убираем дефисы, точки, но сохраняем буквы и цифры
        name = re.sub(r'[^a-zа-яё0-9\s]', '', name)
        return name

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
