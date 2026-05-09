import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        if combine_phases:
            # Собираем все контейнеры этапов (rmpView или Content_Main_цифра)
            phase_containers = soup.find_all('div', class_='rmpView')
            if not phase_containers:
                phase_containers = soup.find_all('div', id=re.compile(r'Content_Main_\d+'))
            combined = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})
            for container in phase_containers:
                phase_stats = self._parse_standings_from_container(container)
                for team, data in phase_stats.items():
                    combined[team]['sets_won'] += data['sets_won']
                    combined[team]['sets_lost'] += data['sets_lost']
                    combined[team]['points_won'] += data['points_won']
                    combined[team]['points_lost'] += data['points_lost']
            stats = combined
        else:
            stats = self._parse_standings_from_container(soup)

        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        print("[DEBUG] Личные встречи для Data Project вводятся вручную")
        return pd.DataFrame()

    def _parse_standings_from_container(self, container):
        # Ищем таблицу в контейнере
        table = container.find('table', class_='RG_Standing_Main')
        if not table:
            table = container.find('table', class_='rgMasterTable')
        if not table:
            # Возможно, таблица без класса – ищем по атрибутам
            table = container.find('table', {'id': re.compile(r'RG_Standing_Main')})
        if not table:
            return {}
        return self._parse_standing_table(table)

    def _parse_standing_table(self, table):
        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')
        stats = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            team_cell = cells[0]
            team_name = team_cell.get_text(strip=True)
            if not team_name:
                link = team_cell.find('a')
                if link:
                    team_name = link.get_text(strip=True)
            if not team_name:
                continue

            sets_won = 0
            sets_lost = 0
            points_won = 0
            points_lost = 0

            # Поиск по ID
            s_w = row.find('span', id='SetsWon')
            s_l = row.find('span', id='SetsLost')
            p_w = row.find('span', id='PuntiFatti') or row.find('span', id='PointsWon')
            p_l = row.find('span', id='PuntiSubiti') or row.find('span', id='PointsLost')
            if s_w and s_l:
                try:
                    sets_won = int(s_w.get_text(strip=True))
                    sets_lost = int(s_l.get_text(strip=True))
                except: pass
            if p_w and p_l:
                try:
                    points_won = int(p_w.get_text(strip=True))
                    points_lost = int(p_l.get_text(strip=True))
                except: pass

            # Эвристика по индексам
            if sets_won == 0 and len(cells) >= 6:
                for i in range(1, len(cells)-1):
                    if cells[i].get_text(strip=True).isdigit() and cells[i+1].get_text(strip=True).isdigit():
                        sets_won = int(cells[i].get_text(strip=True))
                        sets_lost = int(cells[i+1].get_text(strip=True))
                        break
                for i in range(len(cells)-3, len(cells)-1):
                    try:
                        points_won = int(cells[i].get_text(strip=True))
                        points_lost = int(cells[i+1].get_text(strip=True))
                        break
                    except: pass

            if sets_won == 0 and sets_lost == 0:
                continue

            # Очищаем название команды (убираем возможный номер в начале)
            team_name = re.sub(r'^\d+\s*', '', team_name)
            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
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
