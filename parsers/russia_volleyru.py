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
        table = soup.find('table', class_='s-table')
        if not table:
            return None, "Таблица не найдена"

        # Определяем индексы нужных колонок по заголовку thead
        thead = table.find('thead')
        if not thead:
            return None, "Заголовок таблицы не найден"
        
        # Собираем все th из всех строк заголовка
        headers = []
        for row in thead.find_all('tr'):
            for th in row.find_all('th'):
                text = th.get_text(strip=True)
                if text:
                    headers.append(text)
        
        # Индексы в строках данных (td) будут соответствовать порядку th
        # Нужные нам колонки: "И" (матчи), "Пар" (сеты), а также последняя ячейка с очками (data-balls)
        try:
            idx_matches = headers.index('И')
        except ValueError:
            idx_matches = None
        try:
            idx_sets = headers.index('Пар')
        except ValueError:
            idx_sets = None

        # Парсим строки данных (каждая строка с атрибутом data-teamid)
        tbody = table.find('tbody')
        rows = tbody.find_all('tr', attrs={'data-teamid': True})
        if not rows:
            # fallback: строки, содержащие ссылку на команду
            rows = tbody.find_all('tr')
            rows = [row for row in rows if row.find('a', href=re.compile(r'/teams/'))]

        teams = []
        sets_list = []
        points_list = []
        matches_list = []

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            # Название команды – первая ячейка, ссылка
            team_cell = cells[0]
            link = team_cell.find('a')
            team = link.get_text(strip=True) if link else team_cell.get_text(strip=True)
            team = team.split('(')[0].strip()
            if not team:
                continue

            # Сеты: либо из колонки "Пар", либо предпоследняя ячейка
            if idx_sets is not None and idx_sets < len(cells):
                sets_text = cells[idx_sets].get_text(strip=True)
            else:
                # fallback: предпоследняя ячейка
                sets_text = cells[-2].get_text(strip=True) if len(cells) >= 2 else '0:0'
            if ':' not in sets_text:
                sets_text = '0:0'
            sw, sl = map(int, sets_text.split(':'))
            sets_list.append(f"{sw}:{sl}")

            # Очки: всегда в последней ячейке, атрибут data-balls
            last_cell = cells[-1]
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                points_list.append(balls)
            else:
                points_list.append('0:0')

            # Количество матчей: из колонки "И"
            matches = None
            if idx_matches is not None and idx_matches < len(cells):
                matches_text = cells[idx_matches].get_text(strip=True)
                if matches_text.isdigit():
                    matches = int(matches_text)
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
