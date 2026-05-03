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
        def clean(name):
            # Приводим к нижнему регистру, убираем город в скобках, заменяем дефисы на пробелы
            name = name.split('(')[0].strip().lower()
            name = name.replace('ё', 'е')
            return name
        t1 = clean(team1)
        t2 = clean(team2)
        print(f"[DEBUG] Ищем личные встречи: '{t1}' vs '{t2}'")

        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', class_='s-table')
        if not table or 's-table--round' in table.get('class', []):
            print("[DEBUG] Матричная таблица не найдена")
            return pd.DataFrame()

        # Сбор соответствия номеров команд
        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        team_by_num = {}
        raw_names = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            raw = cells[0].get_text(strip=True)
            cleaned = clean(raw)
            num = int(cells[1].get_text(strip=True))
            team_by_num[num] = cleaned
            raw_names[cleaned] = raw

        # Получаем номера выбранных команд
        num_to_team = {v: k for k, v in team_by_num.items()}
        if t1 not in num_to_team or t2 not in num_to_team:
            print(f"[DEBUG] Одна из команд не найдена: {t1} vs {t2}")
            return pd.DataFrame()
        home_num = num_to_team[t1]
        away_num = num_to_team[t2]

        # Заголовки столбцов (номера команд)
        thead = table.find('thead')
        header_row = thead.find('tr')
        ths = header_row.find_all('th')[2:]
        column_numbers = []
        for th in ths:
            txt = th.get_text(strip=True)
            if txt.isdigit():
                column_numbers.append(int(txt))
        # Определяем позицию away_num в списке column_numbers
        try:
            col_idx = column_numbers.index(away_num)
        except ValueError:
            print(f"[DEBUG] Номер {away_num} не найден в заголовках")
            return pd.DataFrame()

        # Ищем строку с home_num
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            if int(cells[1].get_text(strip=True)) == home_num:
                # Ячейка находится по индексу 2 + col_idx
                if 2 + col_idx >= len(cells):
                    print("[DEBUG] Выход за границы ячеек")
                    break
                cell = cells[2 + col_idx]
                divs = cell.find_all('div')
                matches = []
                for idx, div in enumerate(divs):
                    score_text = div.get_text(strip=True)
                    match = re.search(r'(\d+):(\d+)', score_text)
                    if match:
                        hs, aws = match.groups()
                        if idx == 0:
                            matches.append({
                                'Дата': f"Матч {idx+1}",
                                'Хозяева': raw_names[t1],
                                'Гости': raw_names[t2],
                                'Счёт': f"{hs}:{aws}"
                            })
                        else:
                            matches.append({
                                'Дата': f"Матч {idx+1}",
                                'Хозяева': raw_names[t2],
                                'Гости': raw_names[t1],
                                'Счёт': f"{hs}:{aws}"
                            })
                return pd.DataFrame(matches)
        print("[DEBUG] Строка с домашней командой не найдена")
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
