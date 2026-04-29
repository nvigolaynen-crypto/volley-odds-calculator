import re
import requests
from collections import defaultdict
import pandas as pd
from bs4 import BeautifulSoup
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str):
        """Парсит список матчей и возвращает DataFrame с сетами и мячами."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Инициализируем словарь для статистики команд
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                    'points_won': 0, 'points_lost': 0})

        # Поиск всех строк с матчами
        match_rows = soup.find_all('tr', class_='table-game')
        if not match_rows:
            raise ValueError("Не найдено строк с матчами")

        for row in match_rows:
            cells = row.find_all('td')
            if len(cells) < 6:
                continue

            # Извлекаем названия команд
            home_cell = cells[2]
            away_cell = cells[4]
            home_team = self._clean_team_name(home_cell.get_text(strip=True))
            away_team = self._clean_team_name(away_cell.get_text(strip=True))

            # Извлекаем счёт по партиям
            score_span = row.find('span', class_='s-table__rounds-score')
            if not score_span:
                continue
            score_text = score_span.get_text(strip=True).strip('()')

            # Разделяем строку на партии и суммируем очки
            point_pairs = re.findall(r'(\d+):(\d+)', score_text)
            if not point_pairs:
                continue

            home_points = 0
            away_points = 0
            home_sets = 0
            away_sets = 0

            for home_pt, away_pt in point_pairs:
                home_points += int(home_pt)
                away_points += int(away_pt)

            # Определяем победителя партии для подсчёта сетов
            for home_pt, away_pt in point_pairs:
                if int(home_pt) > int(away_pt):
                    home_sets += 1
                else:
                    away_sets += 1

            # Обновляем статистику для команд
            stats[home_team]['sets_won'] += home_sets
            stats[home_team]['sets_lost'] += away_sets
            stats[away_team]['sets_won'] += away_sets
            stats[away_team]['sets_lost'] += home_sets

            stats[home_team]['points_won'] += home_points
            stats[home_team]['points_lost'] += away_points
            stats[away_team]['points_won'] += away_points
            stats[away_team]['points_lost'] += home_points

        # Формируем DataFrame
        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()

    def _clean_team_name(self, name: str) -> str:
        """Очищает название команды от лишних символов."""
        # Удаляем содержимое в скобках (город)
        name = re.sub(r'\s*\([^)]*\)', '', name)
        return name.strip()
