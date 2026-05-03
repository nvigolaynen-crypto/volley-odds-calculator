import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Очистка названий: убираем город в скобках и лишние пробелы, приводим к нижнему регистру
        def clean(name):
            name = name.split('(')[0].strip()
            name = re.sub(r'\s+', ' ', name)
            return name.lower()
        
        t1 = clean(team1)
        t2 = clean(team2)
        print(f"[DEBUG] Ищем встречи: '{t1}' vs '{t2}' на {url}")

        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Находим матричную таблицу
        table = soup.find('table', class_='s-table')
        if not table or 's-table--round' in table.get('class', []):
            print("[DEBUG] Матричная таблица не найдена")
            return pd.DataFrame()

        # Собираем все команды из строк
        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        team_by_num = {}
        raw_names = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            raw = cells[0].get_text(strip=True)
            clean_name = clean(raw)
            num = int(cells[1].get_text(strip=True))
            team_by_num[num] = clean_name
            raw_names[clean_name] = raw

        # Выводим все команды для отладки
        all_teams = list(team_by_num.values())
        print(f"[DEBUG] Команды в матрице: {all_teams}")
        if t1 not in all_teams:
            print(f"[DEBUG] Команда '{t1}' не найдена в матрице")
        if t2 not in all_teams:
            print(f"[DEBUG] Команда '{t2}' не найдена в матрице")

        # Заголовки столбцов (номера команд)
        thead = table.find('thead')
        header_row = thead.find('tr')
        ths = header_row.find_all('th')[2:]
        column_numbers = [int(th.get_text(strip=True)) for th in ths if th.get_text(strip=True).isdigit()]

        # Ищем ячейку, где пересекаются наши команды
        home_num = None
        away_num = None
        for num, name in team_by_num.items():
            if name == t1:
                home_num = num
            if name == t2:
                away_num = num

        if home_num is None or away_num is None:
            print("[DEBUG] Одна из команд не найдена в матрице")
            return pd.DataFrame()

        # Находим строку домашней команды и ячейку с гостем
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            if int(cells[1].get_text(strip=True)) == home_num:
                # Нужный столбец
                col_idx = column_numbers.index(away_num) if away_num in column_numbers else -1
                if col_idx >= 0:
                    cell = cells[2 + col_idx]
                    divs = cell.find_all('div')
                    matches = []
                    for idx, div in enumerate(divs):
                        score_text = div.get_text(strip=True)
                        match = re.search(r'(\d+):(\d+)', score_text)
                        if match:
                            hs, aws = match.groups()
                            if idx == 0:
                                # матч home vs away
                                matches.append({
                                    'Дата': f"Матч {idx+1}",
                                    'Хозяева': raw_names[t1],
                                    'Гости': raw_names[t2],
                                    'Счёт': f"{hs}:{aws}"
                                })
                            else:
                                # матч away vs home
                                matches.append({
                                    'Дата': f"Матч {idx+1}",
                                    'Хозяева': raw_names[t2],
                                    'Гости': raw_names[t1],
                                    'Счёт': f"{hs}:{aws}"
                                })
                    print(f"[DEBUG] Найдено матчей между {t1} и {t2}: {len(matches)}")
                    return pd.DataFrame(matches)
        print("[DEBUG] Ячейка с результатами не найдена")
        return pd.DataFrame()

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
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = cells[0].get_text(strip=True).split('(')[0].strip()
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
            stats[team_name] = {
                'sets_won': sw,
                'sets_lost': sl,
                'points_won': pw,
                'points_lost': pl
            }
        return stats

    def _make_dataframe(self, stats):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        return df.sort_values('sets_won', ascending=False)[['Команда', 'Сеты', 'Мячи']]
