import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin, urlparse
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):

    # ... (методы fetch_stats, _fetch_single_phase, _parse_matrix_table, _make_dataframe остаются без изменений) ...

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Ищет личные встречи на странице текущего этапа или на странице 'Все игры'."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # Сначала пробуем найти на текущей странице
        matches = self._parse_head_to_head_from_url(url, team1, team2)
        if matches:
            return pd.DataFrame(matches)

        # Если не нашли, переходим на страницу "Все игры"
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
        """Парсит личные встречи с конкретной страницы."""
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
