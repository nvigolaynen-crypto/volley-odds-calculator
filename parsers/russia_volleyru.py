import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки: {e}"

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='s-table')
        if not table:
            return None, "Таблица не найдена"

        rows = table.find_all('tr', attrs={'data-teamid': True})
        if not rows:
            rows = table.find_all('tr')
            rows = [row for row in rows if row.find('a', href=re.compile(r'/teams/'))]

        teams = []
        sets_list = []
        points_list = []
        matches_list = []

        for row in rows:
            first_td = row.find('td')
            if not first_td:
                continue
            link = first_td.find('a')
            team = link.get_text(strip=True) if link else first_td.get_text(strip=True)
            if not team:
                continue

            cells = row.find_all('td')
            sets_cell = None
            points_cell = None
            matches_cell = None
            for cell in cells:
                text = cell.get_text(strip=True)
                if ':' in text:
                    if sets_cell is None:
                        sets_cell = text
                    else:
                        points_cell = text
                elif text.isdigit() and 1 <= int(text) <= 50:
                    if matches_cell is None:
                        matches_cell = int(text)
            if sets_cell and points_cell:
                sets_list.append(sets_cell)
                points_list.append(points_cell)
            else:
                sets_list.append('0:0')
                points_list.append('0:0')
            matches_list.append(matches_cell if matches_cell is not None else None)
            teams.append(team)

        if not teams:
            return None, "Не удалось извлечь команды"

        df = pd.DataFrame({
            'Команда': teams,
            'Сеты': sets_list,
            'Мячи': points_list,
            'Матчи': matches_list
        })
        return df, None
