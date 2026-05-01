import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    # ... (Методы fetch_stats, _fetch_single_phase, _parse_matrix_table, _make_dataframe остаются без изменений) ...

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Упрощенный парсер с отладочным выводом."""
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Очищаем только город в скобках
        team1_clean = team1.split('(')[0].strip().lower()
        team2_clean = team2.split('(')[0].strip().lower()
        print(f"[DEBUG] Ищем личные встречи: '{team1_clean}' vs '{team2_clean}'")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки: {e}")
            return pd.DataFrame()

        soup = BeautifulSoup(response.text, 'html.parser')
        # Ищем строки с матчами
        match_rows = soup.find_all('tr', class_='table-game')
        if not match_rows:
            # Если не нашли, пробуем найти любую строку в таблице с матчами
            table = soup.find('table', class_='s-table--round')
            if table:
                match_rows = table.find_all('tr')[1:]

        if not match_rows:
            print("[DEBUG] Таблица с матчами не найдена")
            return pd.DataFrame()

        print(f"[DEBUG] Найдено строк с матчами: {len(match_rows)}")
        matches = []
        for row in match_rows:
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

            # Очищаем названия от города в скобках
            home_clean = home_raw.split('(')[0].strip().lower()
            away_clean = away_raw.split('(')[0].strip().lower()

            # ВЫВОДИМ РЕАЛЬНЫЕ ИМЕНА КОМАНД В ЛОГИ
            if (home_clean == team1_clean and away_clean == team2_clean) or (home_clean == team2_clean and away_clean == team1_clean):
                matches.append({
                    'Дата': date,
                    'Хозяева': home_raw,
                    'Гости': away_raw,
                    'Счёт': total,
                    'Партии': ''
                })
                print(f"[DEBUG] FOUND H2H: home='{home_raw}', away='{away_raw}'")
            # else:
            #     print(f"[DEBUG] SKIP: home='{home_clean}', away='{away_clean}'")

        print(f"[DEBUG] Найдено личных встреч: {len(matches)}")
        return pd.DataFrame(matches)
