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
        def normalize(name):
            return name.strip().lower().split('(')[0].strip()

        team1_norm = normalize(team1)
        team2_norm = normalize(team2)
        print(f"[DEBUG] Поиск личных встреч: {team1_norm} vs {team2_norm}")

        # 1. Пробуем на текущей странице
        matches = self._find_matches_on_page(url, team1_norm, team2_norm, headers)
        if matches:
            print(f"[DEBUG] Найдено {len(matches)} матчей на текущей странице")
            return pd.DataFrame(matches)

        # 2. Ищем страницу "Все игры"
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        allgames_link = None
        for link in soup.find_all('a', href=True):
            if 'allgames' in link.get('href') or 'Все игры' in link.get_text():
                allgames_link = urljoin(url, link.get('href'))
                break
        if allgames_link:
            print(f"[DEBUG] Пробуем страницу 'Все игры': {allgames_link}")
            matches = self._find_matches_on_page(allgames_link, team1_norm, team2_norm, headers)
            if matches:
                print(f"[DEBUG] Найдено {len(matches)} матчей на странице 'Все игры'")
                return pd.DataFrame(matches)
        else:
            print("[DEBUG] Ссылка на 'Все игры' не найдена")

        print("[DEBUG] Личные встречи не найдены")
        return pd.DataFrame()

    def _find_matches_on_page(self, page_url, team1_norm, team2_norm, headers):
        try:
            resp = requests.get(page_url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки {page_url}: {e}")
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        matches_table = soup.find('table', class_='s-table--round')
        if not matches_table:
            print(f"[DEBUG] Таблица s-table--round не найдена на {page_url}")
            return []
        rows = matches_table.find_all('tr', class_='table-game')
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
            sw = sl = 0
            if ':' in sets_text:
                sw, sl = map(int, sets_text.split(':'))
            balls = last_cell.get('data-balls')
            pw = pl = 0
            if balls and ':' in balls:
                pw, pl = map(int, balls.split(':'))
            stats[team_name] = {'sets_won': sw, 'sets_lost': sl, 'points_won': pw, 'points_lost': pl}
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
