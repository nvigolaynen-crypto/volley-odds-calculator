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

        # Получаем список команд из строк (первая колонка) и их номера
        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        team_by_num = {}
        num_by_team = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            raw = cells[0].get_text(strip=True)
            cleaned = clean(raw)
            num = int(cells[1].get_text(strip=True))
            team_by_num[num] = cleaned
            num_by_team[cleaned] = num

        # Получаем список команд из заголовков столбцов (вторая строка thead)
        thead = table.find('thead')
        header_row = thead.find('tr')
        ths = header_row.find_all('th')[2:]  # первые два пропускаем
        column_teams = []
        column_nums = []
        for th in ths:
            # В заголовках может быть текст с названием команды или номер
            text = th.get_text(strip=True)
            if text.isdigit():
                column_nums.append(int(text))
                # Найдём название команды по номеру
                if int(text) in team_by_num:
                    column_teams.append(team_by_num[int(text)])
            else:
                # Если текст не цифра, то это, возможно, название команды (но редкий случай)
                column_teams.append(clean(text))
        print(f"[DEBUG] Команды в столбцах: {column_teams}")

        # Ищем строку с командой t1
        home_row = None
        home_num = num_by_team.get(t1)
        if home_num is None:
            print(f"[DEBUG] Команда {t1} не найдена в строках")
            return pd.DataFrame()
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            if int(cells[1].get_text(strip=True)) == home_num:
                home_row = row
                break
        if not home_row:
            print("[DEBUG] Строка с домашней командой не найдена")
            return pd.DataFrame()

        # Находим индекс столбца, соответствующего t2
        try:
            col_idx = column_teams.index(t2)
        except ValueError:
            # Если не нашли, пробуем через номера
            away_num = num_by_team.get(t2)
            if away_num is None:
                print(f"[DEBUG] Команда {t2} не найдена в столбцах")
                return pd.DataFrame()
            try:
                col_idx = column_nums.index(away_num)
            except ValueError:
                print("[DEBUG] Номер команды не найден в заголовках")
                return pd.DataFrame()

        # Ячейка результатов находится на позиции 2 + col_idx
        cells = home_row.find_all('td')
        if 2 + col_idx >= len(cells):
            print("[DEBUG] Выход за границы ячеек")
            return pd.DataFrame()
        cell = cells[2 + col_idx]
        divs = cell.find_all('div')
        matches = []
        for idx, div in enumerate(divs):
            score_text = div.get_text(strip=True)
            score_match = re.search(r'(\d+):(\d+)', score_text)
            if not score_match:
                continue
            hs, aws = score_match.groups()
            if idx == 0:
                # Первый матч: домашняя команда t1, гостевая t2
                matches.append({
                    'Дата': '1-й круг',
                    'Хозяева': team1,
                    'Гости': team2,
                    'Счёт': f"{hs}:{aws}"
                })
            else:
                # Второй матч: домашняя команда t2, гостевая t1
                matches.append({
                    'Дата': '2-й круг',
                    'Хозяева': team2,
                    'Гости': team1,
                    'Счёт': f"{hs}:{aws}"
                })
        print(f"[DEBUG] Найдено матчей: {len(matches)}")
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
