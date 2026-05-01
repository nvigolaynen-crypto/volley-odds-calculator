import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        team1_norm = team1.split('(')[0].strip().lower()
        team2_norm = team2.split('(')[0].strip().lower()
        print(f"[DEBUG] Поиск личных встреч: {team1_norm} vs {team2_norm}")

        # 1. Сначала пробуем на текущей странице
        matches = self._find_matches_on_page(url, team1_norm, team2_norm, headers)
        if matches:
            return pd.DataFrame(matches)

        # 2. Ищем страницу "Все игры"
        allgames_link = self._find_allgames_link(url, headers)
        if allgames_link:
            print(f"[DEBUG] Пробуем страницу 'Все игры': {allgames_link}")
            matches = self._find_matches_on_page(allgames_link, team1_norm, team2_norm, headers)
            if matches:
                return pd.DataFrame(matches)
        else:
            print("[DEBUG] Ссылка на 'Все игры' не найдена")

        # 3. Если всё равно не нашли, пробуем перебрать возможные страницы с турами
        base_url = url.split('?')[0]
        for round_num in range(1, 31):
            round_url = f"{base_url}?round={round_num}"
            matches = self._find_matches_on_page(round_url, team1_norm, team2_norm, headers)
            if matches:
                return pd.DataFrame(matches)

        print("[DEBUG] Личные встречи не найдены")
        return pd.DataFrame()

    def _find_allgames_link(self, url, headers):
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if 'allgames' in href or 'Все игры' in link.get_text():
                return urljoin(url, href)
        return None

    def _find_matches_on_page(self, page_url, team1_norm, team2_norm, headers):
        try:
            resp = requests.get(page_url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки {page_url}: {e}")
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Ищем таблицу матчей (s-table--round или любую с table-game)
        table = soup.find('table', class_='s-table--round')
        if not table:
            # Ищем любую таблицу, содержащую строки с классом table-game
            tables = soup.find_all('table')
            for tbl in tables:
                if tbl.find('tr', class_='table-game'):
                    table = tbl
                    print("[DEBUG] Найдена таблица с class=table-game")
                    break
        if not table:
            print(f"[DEBUG] Таблица матчей не найдена на {page_url}")
            return []
        rows = table.find_all('tr', class_='table-game')
        if not rows:
            # Если нет строк с классом, берём все строки кроме первой (заголовок)
            rows = table.find_all('tr')[1:]
        print(f"[DEBUG] Найдено строк с матчами: {len(rows)}")
        matches = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            home = cells[2].get_text(strip=True).split('(')[0].strip().lower()
            away = cells[4].get_text(strip=True).split('(')[0].strip().lower()
            if (home == team1_norm and away == team2_norm) or (home == team2_norm and away == team1_norm):
                date = cells[0].get_text(strip=True)
                total_span = row.find('span', class_='s-table__total-score')
                total = total_span.get_text(strip=True) if total_span else ''
                rounds_span = row.find('span', class_='s-table__rounds-score')
                rounds = rounds_span.get_text(strip=True) if rounds_span else ''
                matches.append({
                    'Дата': date,
                    'Хозяева': cells[2].get_text(strip=True),
                    'Гости': cells[4].get_text(strip=True),
                    'Счёт': total,
                    'Партии': rounds
                })
        return matches

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
