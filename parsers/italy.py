import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class ItalyParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """
        Парсит турнирную таблицу итальянской волейбольной лиги (legavolley.it).
        Возвращает DataFrame с колонками: Команда, Сеты, Мячи.
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем таблицу с id="GareGiornata" (регистр важен)
        table = soup.find('table', id='GareGiornata')
        if not table:
            raise ValueError("Не найдена таблица с результатами (id='GareGiornata')")

        stats = {}
        # Все строки с классом "EvenRow" содержат данные команд
        rows = table.find_all('tr', id='EvenRow')
        if not rows:
            rows = table.find_all('tr')[2:]  # запасной вариант

        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 14:
                continue

            # Извлекаем название команды (ячейка 2, содержит span.pos и текст)
            team_cell = cells[2].get_text(strip=True)
            # Удаляем номер позиции (например, "1 " или "1.")
            team_name = re.sub(r'^\d+\.?\s*', '', team_cell).strip()

            # Выигранные и проигранные сеты (колонки Vinti и Persi)
            sets_won_text = cells[10].get_text(strip=True)
            sets_lost_text = cells[11].get_text(strip=True)
            # Набранные и пропущенные очки (колонки Fatti и Subiti)
            points_won_text = cells[12].get_text(strip=True)
            points_lost_text = cells[13].get_text(strip=True)

            # Преобразуем в числа (заменяем запятые на точки, если есть)
            try:
                sets_won = int(sets_won_text)
                sets_lost = int(sets_lost_text)
                points_won = float(points_won_text.replace(',', '.')) if ',' in points_won_text else int(points_won_text)
                points_lost = float(points_lost_text.replace(',', '.')) if ',' in points_lost_text else int(points_lost_text)
            except (ValueError, IndexError):
                continue

            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }

        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """
        Личные встречи для Италии вводятся вручную.
        """
        print("[DEBUG] Личные встречи для Италии вводятся вручную")
        return pd.DataFrame()

    def _make_dataframe(self, stats):
        if not stats:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']]
