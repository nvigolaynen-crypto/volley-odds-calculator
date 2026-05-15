import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        def clean(name):
            return name.split('(')[0].strip().lower()
        t1 = clean(team1)
        t2 = clean(team2)
        print(f"[DEBUG] Поиск личных встреч: '{t1}' vs '{t2}'")

        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', class_='s-table')
        if not table or 's-table--round' in table.get('class', []):
            print("[DEBUG] Матричная таблица не найдена")
            return pd.DataFrame()

        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        team_num_by_name = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            raw = cells[0].get_text(strip=True)
            cleaned = clean(raw)
            num = int(cells[1].get_text(strip=True))
            team_num_by_name[cleaned] = num

        if t1 not in team_num_by_name or t2 not in team_num_by_name:
            print("[DEBUG] Одна из команд не найдена")
            return pd.DataFrame()

        home_num = team_num_by_name[t1]
        away_num = team_num_by_name[t2]

        cell = soup.find('td', {'data-i': str(home_num), 'data-j': str(away_num)})
        if not cell:
            cell = soup.find('td', {'data-i': str(away_num), 'data-j': str(home_num)})
        if not cell:
            print("[DEBUG] Ячейка не найдена")
            return pd.DataFrame()

        divs = cell.find_all('div')
        matches = []
        for idx, div in enumerate(divs):
            score_text = div.get_text(strip=True)
            m = re.search(r'(\d+):(\d+)', score_text)
            if not m:
                continue
            hs, aws = m.groups()
            if cell.get('data-i') == str(home_num):
                if idx == 0:
                    matches.append({'Дата': "1-й круг", 'Хозяева': team1, 'Гости': team2, 'Счёт': f"{hs}:{aws}"})
                else:
                    matches.append({'Дата': "2-й круг", 'Хозяева': team2, 'Гости': team1, 'Счёт': f"{hs}:{aws}"})
            else:
                if idx == 0:
                    matches.append({'Дата': "1-й круг", 'Хозяева': team2, 'Гости': team1, 'Счёт': f"{hs}:{aws}"})
                else:
                    matches.append({'Дата': "2-й круг", 'Хозяева': team1, 'Гости': team2, 'Счёт': f"{hs}:{aws}"})
        return pd.DataFrame(matches)

    def _fetch_single_phase(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table or 's-table--round' in matrix_table.get('class', []):
            raise ValueError("Не найдена матричная таблица")
        return self._parse_matrix_table(matrix_table)

    def _parse_matrix_table(self, table):
        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        stats = {}
        
        # Ищем индекс колонки "И" по заголовку
        thead = table.find('thead')
        matches_col_idx = None
        if thead:
            for row in thead.find_all('tr'):
                ths = row.find_all('th')
                for idx, th in enumerate(ths):
                    if th.get_text(strip=True) == 'И':
                        matches_col_idx = idx
                        break
                if matches_col_idx is not None:
                    break
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = cells[0].get_text(strip=True).split('(')[0].strip()
            # Последняя ячейка содержит сеты и очки (как в рабочей версии)
            last_cell = cells[-1]
            sets_text = last_cell.get_text(strip=True)
            if ':' in sets_text:
                sw, sl = map(int, sets_text.split(':'))
            else:
                sw = sl = 0
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                pw, pl = map(int, balls.split(':'))
            else:
                pw = pl = 0
            
            # Количество матчей из колонки "И"
            matches = None
            if matches_col_idx is not None and matches_col_idx < len(cells):
                matches_text = cells[matches_col_idx].get_text(strip=True)
                if matches_text.isdigit():
                    matches = int(matches_text)
            # Если не нашли, оставляем None (будет оценка по сетам в app.py)
            
            stats[team_name] = {
                'sets_won': sw,
                'sets_lost': sl,
                'points_won': pw,
                'points_lost': pl,
                'matches': matches
            }
        return stats

    def _make_dataframe(self, stats):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        if 'matches' in df.columns:
            df = df.rename(columns={'matches': 'Матчи'})
        else:
            df['Матчи'] = None
        return df.sort_values('sets_won', ascending=False)[['Команда', 'Сеты', 'Мячи', 'Матчи']]
