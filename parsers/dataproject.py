import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from .base_parser import BaseParser

class DataProjectParser(BaseParser):

    # ... (методы fetch_stats и _parse_standings_from_container остаются теми же, что и в предыдущей версии) ...
    # ... (методы _parse_standings_table и _make_dataframe также без изменений) ...

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Формирует URL страницы матчей (CompetitionMatches.aspx) и парсит личные встречи."""
        # Извлекаем параметры ID и PID из исходного URL
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        competition_id = query_params.get('ID', [None])[0]
        phase_id = query_params.get('PID', [None])[0]

        if not competition_id:
            return pd.DataFrame()

        # Формируем URL страницы матчей
        base_path = parsed.path.replace('CompetitionStandings.aspx', 'CompetitionMatches.aspx')
        if base_path == parsed.path:
            base_path = "/CompetitionMatches.aspx"

        new_query = {}
        if competition_id:
            new_query['ID'] = competition_id
        if phase_id:
            new_query['PID'] = phase_id

        matches_url = urlunparse((parsed.scheme, parsed.netloc, base_path, '', urlencode(new_query), ''))

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(matches_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Ищем таблицу RadGrid, которая обычно содержит список матчей
        matches_table = soup.find('table', class_='rgMasterTable')
        if not matches_table:
            # Пробуем найти таблицу с другим классом, если не нашли основную
            matches_table = soup.find('table', class_='RadGrid')

        if not matches_table:
            return pd.DataFrame()

        rows = matches_table.find_all('tr', class_='rgRow') + matches_table.find_all('tr', class_='rgAltRow')
        head_to_head = []

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue

            # Извлекаем данные из ячеек
            try:
                # Дата и время могут быть в одной ячейке или в разных
                datetime_cell = cells[0].get_text(strip=True)
                # Разделяем дату и время, если нужно
                date_parts = datetime_cell.split()
                date = date_parts[0] if date_parts else ''
                
                # Названия команд — обычно в 3-й и 4-й ячейках
                home = cells[2].get_text(strip=True)
                away = cells[3].get_text(strip=True)
                
                # Счёт — в 5-й ячейке
                score = cells[4].get_text(strip=True)
                
                # Проверяем, что это матч между нужными командами
                if (home == team1 and away == team2) or (home == team2 and away == team1):
                    head_to_head.append({
                        'Дата': date,
                        'Хозяева': home,
                        'Гости': away,
                        'Счёт': score
                    })
            except IndexError:
                continue

        return pd.DataFrame(head_to_head)

    # ... (остальные методы без изменений) ...
