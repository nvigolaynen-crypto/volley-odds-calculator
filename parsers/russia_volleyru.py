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
        print(f"[DEBUG] Поиск {t1} vs {t2}")

        # Формируем URL страницы "Все игры"
        if 'predvaritelnyy' in url:
            allgames_url = url.replace('predvaritelnyy', 'allgames')
        else:
            allgames_url = url
        print(f"[DEBUG] Загружаем: {allgames_url}")

        try:
            resp = requests.get(allgames_url, headers=headers, timeout=15)
            resp.raise_for_status()
            print(f"[DEBUG] Статус: {resp.status_code}, длина HTML: {len(resp.text)}")
            # Сохраняем HTML для отладки (на Render файл будет в текущей директории)
            with open('debug_volley.html', 'w', encoding='utf-8') as f:
                f.write(resp.text)
            print("[DEBUG] HTML сохранён в debug_volley.html")
        except Exception as e:
            print(f"[DEBUG] Ошибка: {e}")
            return pd.DataFrame()

        soup = BeautifulSoup(resp.text, 'html.parser')
        # Ищем любую таблицу, содержащую строки с классом table-game
        table = None
        for tbl in soup.find_all('table'):
            if tbl.find('tr', class_='table-game'):
                table = tbl
                print("[DEBUG] Найдена таблица с class='table-game'")
                break
        if not table:
            # Если не нашли, пробуем искать по классу s-table--round
            table = soup.find('table', class_='s-table--round')
        if not table:
            # Если всё равно не нашли, выводим фрагмент HTML и возвращаем пустой результат
            print("[DEBUG] Таблица не найдена. HTML фрагмент (первые 2000 символов):")
            print(resp.text[:2000])
            return pd.DataFrame()

        rows = table.find_all('tr', class_='table-game')
        if not rows:
            # Если нет строк с классом, берём все строки кроме первой (заголовок)
            rows = table.find_all('tr')[1:]
        print(f"[DEBUG] Найдено строк: {len(rows)}")

        matches = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue
            date = cells[0].get_text(strip=True)
            home_raw = cells[2].get_text(strip=True)
            away_raw = cells[4].get_text(strip=True)
            # Ищем ячейку со счётом (обычно последняя или предпоследняя)
            score_span = row.find('span', class_='s-table__total-score')
            if not score_span:
                # Если нет span, пробуем взять текст из последней ячейки
                score_text = cells[-1].get_text(strip=True)
                score_match = re.search(r'(\d+:\d+)', score_text)
                total = score_match.group(1) if score_match else ''
            else:
                total = score_span.get_text(strip=True)
            home = clean(home_raw)
            away = clean(away_raw)

            if (home == t1 and away == t2) or (home == t2 and away == t1):
                matches.append({
                    'Дата': date,
                    'Хозяева': home_raw,
                    'Гости': away_raw,
                    'Счёт': total,
                })
        print(f"[DEBUG] Найдено встреч: {len(matches)}")
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
