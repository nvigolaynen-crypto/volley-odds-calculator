import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    # ------------------------------------------------------------
    # Основной метод парсинга статистики (сеты и мячи)
    # ------------------------------------------------------------
    def fetch_stats(self, url: str, combine_phases: bool = False):
        # Для России объединение этапов не требуется (игнорируем combine_phases)
        stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    # ------------------------------------------------------------
    # Метод для поиска личных встреч (только на текущей странице)
    # ------------------------------------------------------------
    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Ищет личные встречи на указанной странице матчей (без перехода на 'Все игры')."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        team1_norm = self._normalize_team_name(team1)
        team2_norm = self._normalize_team_name(team2)
        print(f"[DEBUG] Поиск личных встреч: {team1_norm} vs {team2_norm} на {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки страницы: {e}")
            return pd.DataFrame()

        soup = BeautifulSoup(response.text, 'html.parser')
        # Ищем строки с матчами на странице (класс table-game)
        match_rows = soup.find_all('tr', class_='table-game')
        if not match_rows:
            print("[DEBUG] Таблица с матчами не найдена.")
            return pd.DataFrame()

        print(f"[DEBUG] Найдено строк с матчами: {len(match_rows)}")
        matches = []
        for row in match_rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            date = cells[0].get_text(strip=True)
            home_raw = cells[2].get_text(strip=True)
            away_raw = cells[4].get_text(strip=True)
            score_cell = cells[-1].get_text(strip=True)  # последняя ячейка содержит счёт и партии

            home = self._normalize_team_name(home_raw)
            away = self._normalize_team_name(away_raw)

            if (home == team1_norm and away == team2_norm) or (home == team2_norm and away == team1_norm):
                # Извлекаем общий счёт (например, "3:1")
                score_match = re.search(r'(\d+:\d+)', score_cell)
                score = score_match.group(1) if score_match else ''
                # Извлекаем партии (например, "25:20, 22:25, 25:18")
                rounds_match = re.search(r'\((.*?)\)', score_cell)
                rounds = rounds_match.group(1) if rounds_match else ''
                matches.append({
                    'Дата': date,
                    'Хозяева': home_raw,
                    'Гости': away_raw,
                    'Счёт': score,
                    'Партии': rounds
                })
        return pd.DataFrame(matches)

    def _normalize_team_name(self, name: str) -> str:
        """Приводит название команды к нижнему регистру и удаляет город в скобках."""
        return name.split('(')[0].strip().lower()

    # ------------------------------------------------------------
    # Вспомогательные методы для парсинга турнирной таблицы
    # ------------------------------------------------------------
    def _fetch_single_phase(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
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
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']]
