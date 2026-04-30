import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin, urlparse
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Ищет личные встречи на странице текущего этапа или на странице 'Все игры'."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Сначала пробуем на текущей странице
        matches = self._parse_head_to_head_from_url(url, team1, team2)
        if matches:
            return pd.DataFrame(matches)
        # Если не нашли, пробуем перейти на страницу "Все игры"
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        # Ищем ссылку на "Все игры" (allgames)
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        allgames_link = None
        for link in soup.find_all('a', href=True):
            if 'allgames' in link.get('href') or 'Все игры' in link.get_text():
                allgames_link = urljoin(base, link.get('href'))
                break
        if allgames_link:
            matches = self._parse_head_to_head_from_url(allgames_link, team1, team2)
            if matches:
                return pd.DataFrame(matches)
        return pd.DataFrame()

    def _parse_head_to_head_from_url(self, url, team1, team2):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        matches_table = soup.find('table', class_='s-table--round')
        if not matches_table:
            return []
        matches = []
        rows = matches_table.find_all('tr', class_='table-game')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            home = cells[2].get_text(strip=True)
            away = cells[4].get_text(strip=True)
            if (home == team1 and away == team2) or (home == team2 and away == team1):
                date = cells[0].get_text(strip=True)
                total_span = row.find('span', class_='s-table__total-score')
                total = total_span.get_text(strip=True) if total_span else ''
                rounds_span = row.find('span', class_='s-table__rounds-score')
                rounds = rounds_span.get_text(strip=True) if rounds_span else ''
                matches.append({
                    'Дата': date,
                    'Хозяева': home,
                    'Гости': away,
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
