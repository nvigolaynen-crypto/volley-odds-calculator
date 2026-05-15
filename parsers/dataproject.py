import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки: {e}"

        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', class_='rgMasterTable')
        if not table:
            return None, "Таблица не найдена"

        rows = table.find_all('tr', class_=re.compile(r'RG_Standing_Main_AltBackColor'))
        if not rows:
            rows = table.find_all('tr')
            rows = [row for row in rows if row.find('span', id=re.compile(r'TeamName'))]

        teams = []
        sets_won_list = []
        sets_lost_list = []
        points_won_list = []
        points_lost_list = []
        matches_list = []

        for row in rows:
            team_span = row.find('span', id=re.compile(r'TeamName'))
            if not team_span:
                continue
            team = team_span.get_text(strip=True)
            if not team:
                continue
            teams.append(team)

            matches_span = row.find('span', id=re.compile(r'MatchesPlayed'))
            if matches_span:
                matches_text = matches_span.get_text(strip=True)
                matches = int(matches_text) if matches_text.isdigit() else None
            else:
                matches = None
            matches_list.append(matches)

            sets_won_span = row.find('span', id=re.compile(r'SetsWon'))
            sets_lost_span = row.find('span', id=re.compile(r'SetsLost'))
            sets_won = int(sets_won_span.get_text(strip=True)) if sets_won_span else 0
            sets_lost = int(sets_lost_span.get_text(strip=True)) if sets_lost_span else 0
            sets_won_list.append(sets_won)
            sets_lost_list.append(sets_lost)

            points_won_span = row.find('span', id=re.compile(r'PuntiFatti'))
            points_lost_span = row.find('span', id=re.compile(r'PuntiSubiti'))
            points_won = int(points_won_span.get_text(strip=True)) if points_won_span else 0
            points_lost = int(points_lost_span.get_text(strip=True)) if points_lost_span else 0
            points_won_list.append(points_won)
            points_lost_list.append(points_lost)

        if not teams:
            return None, "Не удалось извлечь команды"

        df = pd.DataFrame({
            'Команда': teams,
            'Сеты': [f"{w}:{l}" for w, l in zip(sets_won_list, sets_lost_list)],
            'Мячи': [f"{w}:{l}" for w, l in zip(points_won_list, points_lost_list)],
            'Матчи': matches_list
        })
        return df, None
