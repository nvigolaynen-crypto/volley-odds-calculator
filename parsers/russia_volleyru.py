import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str):
        """
        Парсит страницу предварительного этапа volley.ru и возвращает df с колонками:
        Команда, Сеты (выигранные:проигранные), Мячи (забито:пропущено)
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Ищем основную матричную таблицу (без класса --round)
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table or 's-table--round' in matrix_table.get('class', []):
            raise ValueError("Не найдена таблица с результатами (матрица)")

        # Парсим таблицу
        stats = self._parse_matrix_table(matrix_table)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()  # второй df для деталей матчей (не используется)

    def _parse_matrix_table(self, table):
        # Получаем номера команд из заголовков столбцов (начиная с 3-го)
        thead = table.find('thead')
        if not thead:
            raise ValueError("Нет заголовка таблицы")
        header_row = thead.find('tr')
        ths = header_row.find_all('th')
        # Пропускаем первые два (пустой и "№")
        column_numbers = []
        for th in ths[2:]:
            text = th.get_text(strip=True)
            if text.isdigit():
                column_numbers.append(int(text))

        tbody = table.find('tbody')
        rows = tbody.find_all('tr')

        # Словарь: номер команды -> её название
        team_by_num = {}
        # Словарь для накопления статистики
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                    'points_won': 0, 'points_lost': 0})

        # Первый проход: извлекаем названия команд и мячи (data-balls)
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            # Название команды может быть в <a> или просто текст
            team_cell = cells[0]
            team_name = team_cell.get_text(strip=True)
            # Номер команды (второй столбец)
            team_number = int(cells[1].get_text(strip=True))
            team_by_num[team_number] = team_name

            # Мячи: последний столбец имеет атрибут data-balls
            last_cell = cells[-1]
            balls_data = last_cell.get('data-balls')
            if balls_data and ':' in balls_data:
                won, lost = map(int, balls_data.split(':'))
                stats[team_name]['points_won'] = won
                stats[team_name]['points_lost'] = lost

        # Второй проход: собираем сеты из ячеек (оба круга)
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            home_num = int(cells[1].get_text(strip=True))
            home_name = team_by_num.get(home_num)
            if not home_name:
                continue

            # Ячейки с результатами идут с индекса 2 до предпоследних 5-ти (после них И, В, П, Оч, Пар)
            result_cells = cells[2:-5]
            for col_idx, cell in enumerate(result_cells):
                if col_idx >= len(column_numbers):
                    break
                away_num = column_numbers[col_idx]
                away_name = team_by_num.get(away_num)
                if not away_name:
                    continue

                # Внутри ячейки может быть один или два <div> (два матча)
                divs = cell.find_all('div')
                if not divs:
                    # Если нет <div>, возможно, текст внутри <td>
                    text = cell.get_text(strip=True)
                    if text and ':' in text:
                        # Разделяем по строкам (первый и второй матч)
                        lines = text.splitlines()
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            score_match = re.search(r'(\d+):(\d+)', line)
                            if score_match:
                                hs, aws = map(int, score_match.groups())
                                # В таком случае считаем, что это матч home vs away
                                stats[home_name]['sets_won'] += hs
                                stats[home_name]['sets_lost'] += aws
                                stats[away_name]['sets_won'] += aws
                                stats[away_name]['sets_lost'] += hs
                    continue

                # Обработка первого матча (home vs away)
                if len(divs) >= 1:
                    text = divs[0].get_text(strip=True)
                    score_match = re.search(r'(\d+):(\d+)', text)
                    if score_match:
                        hs, aws = map(int, score_match.groups())
                        stats[home_name]['sets_won'] += hs
                        stats[home_name]['sets_lost'] += aws
                        stats[away_name]['sets_won'] += aws
                        stats[away_name]['sets_lost'] += hs

                # Обработка второго матча (away vs home)
                if len(divs) >= 2:
                    text = divs[1].get_text(strip=True)
                    score_match = re.search(r'(\d+):(\d+)', text)
                    if score_match:
                        hs, aws = map(int, score_match.groups())
                        stats[away_name]['sets_won'] += hs
                        stats[away_name]['sets_lost'] += aws
                        stats[home_name]['sets_won'] += aws
                        stats[home_name]['sets_lost'] += hs

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
