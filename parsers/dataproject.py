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
        
        # Поиск таблицы с результатами (RG_Standing_Main или rgMasterTable)
        table = soup.find('table', class_='RG_Standing_Main')
        if not table:
            table = soup.find('table', class_='rgMasterTable')
        if not table:
            raise ValueError("Не найдена таблица с результатами")
        
        stats = self._parse_standing_table(table)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()
    
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
            
            # Поиск по ID (стандарт Data Project)
            sets_won_span = row.find('span', id='SetsWon')
            sets_lost_span = row.find('span', id='SetsLost')
            points_won_span = row.find('span', id='PuntiFatti') or row.find('span', id='PointsWon')
            points_lost_span = row.find('span', id='PuntiSubiti') or row.find('span', id='PointsLost')
            
            if sets_won_span and sets_lost_span:
                try:
                    sets_won = int(sets_won_span.get_text(strip=True))
                    sets_lost = int(sets_lost_span.get_text(strip=True))
                except:
                    pass
            if points_won_span and points_lost_span:
                try:
                    points_won = int(points_won_span.get_text(strip=True))
                    points_lost = int(points_lost_span.get_text(strip=True))
                except:
                    pass
            
            # Если не нашли по ID, пробуем эвристику по индексам
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
                    except:
                        pass
            
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
    
    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        print("[DEBUG] Личные встречи для Data Project вводятся вручную")
        return pd.DataFrame()
