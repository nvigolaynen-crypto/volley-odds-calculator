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

        tbody = table.find('tbody')
        rows = tbody.find_all('tr', attrs={'data-teamid': True})
        if not rows:
            rows = tbody.find_all('tr')
            rows = [row for row in rows if row.find('a', href=re.compile(r'/teams/'))]

        teams = []
        sets_list = []
        points_list = []
        matches_list = []

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            team_cell = cells[0]
            link = team_cell.find('a')
            team = link.get_text(strip=True) if link else team_cell.get_text(strip=True)
            team = team.split('(')[0].strip()
            if not team:
                continue

            sets_cell = cells[-1]
            sets_text = sets_cell.get_text(strip=True)
            if ':' not in sets_text:
                sets_text = '0:0'
            sets_list.append(sets_text)

            balls = sets_cell.get('data-balls')
            if balls and ':' in balls:
                points_list.append(balls)
            else:
                points_list.append('0:0')

            matches_cell = cells[-5]
            matches_text = matches_cell.get_text(strip=True)
            if matches_text.isdigit():
                matches = int(matches_text)
            else:
                matches = None
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
