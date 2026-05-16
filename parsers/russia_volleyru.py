import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки: {e}"

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Пробуем разные классы таблиц
        table = soup.find('table', class_='s-table')
        if not table:
            table = soup.find('table', class_='table')
        if not table:
            table = soup.find('table', attrs={'data-name': 'tournament-table'})
        if not table:
            return None, "Таблица не найдена"

        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        rows = tbody.find_all('tr')
        # Фильтруем строки, которые содержат ссылку на команду или атрибут data-teamid
        team_rows = []
        for row in rows:
            if row.get('data-teamid'):
                team_rows.append(row)
            elif row.find('a', href=re.compile(r'/teams/')):
                team_rows.append(row)
        if not team_rows:
            team_rows = rows  # fallback

        teams = []
        sets_list = []
        points_list = []
        matches_list = []

        for row in team_rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue

            # Название команды – обычно первая ячейка с ссылкой
            first_cell = cells[0]
            link = first_cell.find('a')
            if link:
                team = link.get_text(strip=True)
            else:
                team = first_cell.get_text(strip=True)
            team = team.split('(')[0].strip()
            if not team:
                continue

            # Поиск ячейки с сетами (часто последняя, но может быть предпоследняя)
            sets_cell = None
            for cell in reversed(cells):
                text = cell.get_text(strip=True)
                if ':' in text and re.match(r'\d+:\d+', text):
                    sets_cell = cell
                    break
            if not sets_cell:
                continue
            sets_text = sets_cell.get_text(strip=True)
            if ':' not in sets_text:
                sets_text = "0:0"
            sets_list.append(sets_text)

            # Очки (мячи) – ищем по атрибуту data-balls или по соседней ячейке
            balls = sets_cell.get('data-balls')
            if balls and ':' in balls:
                points_list.append(balls)
            else:
                points_text = "0:0"
                idx = cells.index(sets_cell) if sets_cell in cells else -1
                if idx > 0:
                    prev_cell = cells[idx-1]
                    prev_text = prev_cell.get_text(strip=True)
                    if ':' in prev_text:
                        points_text = prev_text
                points_list.append(points_text)

            # Количество матчей (обычно колонка "И")
            matches = None
            for i, cell in enumerate(cells):
                if cell.get_text(strip=True).isdigit() and i in (len(cells)-5, len(cells)-4):
                    matches = int(cell.get_text(strip=True))
                    break
            matches_list.append(matches)
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
