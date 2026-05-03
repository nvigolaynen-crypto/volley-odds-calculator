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
        """
        Ищет личные встречи в матричной таблице (s-table) на странице предварительного этапа.
        В ячейках матрицы хранятся результаты двух матчей между командами.
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        def clean(name):
            # Убираем город в скобках, лишние пробелы, приводим к нижнему регистру
            return name.split('(')[0].strip().lower()
        
        t1 = clean(team1)
        t2 = clean(team2)
        print(f"[DEBUG] Поиск личных встреч {t1} vs {t2} на {url}")

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка: {e}")
            return pd.DataFrame()

        soup = BeautifulSoup(resp.text, 'html.parser')
        # Находим матричную таблицу (s-table без --round)
        table = soup.find('table', class_='s-table')
        if not table or 's-table--round' in table.get('class', []):
            print("[DEBUG] Матричная таблица не найдена")
            return pd.DataFrame()

        # Получаем заголовки (номера команд)
        thead = table.find('thead')
        header_row = thead.find('tr')
        ths = header_row.find_all('th')[2:]  # пропускаем пустой и "№"
        team_numbers = []
        for th in ths:
            num_text = th.get_text(strip=True)
            if num_text.isdigit():
                team_numbers.append(int(num_text))

        tbody = table.find('tbody')
        rows = tbody.find_all('tr')
        # Сопоставление номера команды с названием
        team_by_num = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = clean(cells[0].get_text(strip=True))
            team_num = int(cells[1].get_text(strip=True))
            team_by_num[team_num] = team_name

        # Выводим все команды для отладки
        all_teams = list(team_by_num.values())
        print(f"[DEBUG] Команды в матрице: {all_teams}")
        if t1 not in all_teams:
            print(f"[DEBUG] Команда '{t1}' не найдена в матрице")
        if t2 not in all_teams:
            print(f"[DEBUG] Команда '{t2}' не найдена в матрице")

        # Перебираем ячейки матрицы
        matches = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            home_num = int(cells[1].get_text(strip=True))
            home_name = team_by_num.get(home_num)
            if not home_name:
                continue
            # Ячейки результатов (начиная с 2-й, до предпоследних 5-ти)
            result_cells = cells[2:-5]
            for col_idx, cell in enumerate(result_cells):
                if col_idx >= len(team_numbers):
                    break
                away_num = team_numbers[col_idx]
                away_name = team_by_num.get(away_num)
                if not away_name:
                    continue
                # В ячейке может быть один или два div (два матча)
                divs = cell.find_all('div')
                for idx, div in enumerate(divs):
                    score_text = div.get_text(strip=True)
                    match = re.search(r'(\d+):(\d+)', score_text)
                    if not match:
                        continue
                    hs, aws = match.groups()
                    # Первый div: home vs away, второй div: away vs home
                    if idx == 0:
                        if (home_name == t1 and away_name == t2) or (home_name == t2 and away_name == t1):
                            matches.append({
                                'Дата': '(из таблицы)',
                                'Хозяева': home_name,
                                'Гости': away_name,
                                'Счёт': f"{hs}:{aws}"
                            })
                    else:
                        if (away_name == t1 and home_name == t2) or (away_name == t2 and home_name == t1):
                            matches.append({
                                'Дата': '(из таблицы)',
                                'Хозяева': away_name,
                                'Гости': home_name,
                                'Счёт': f"{hs}:{aws}"
                            })
        # Убираем дубликаты
        seen = set()
        unique = []
        for m in matches:
            key = (m['Хозяева'], m['Гости'], m['Счёт'])
            if key not in seen:
                seen.add(key)
                unique.append(m)
        print(f"[DEBUG] Найдено личных встреч в матрице: {len(unique)}")
        return pd.DataFrame(unique)

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
