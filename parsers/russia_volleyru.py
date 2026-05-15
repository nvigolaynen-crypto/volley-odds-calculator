import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """
        Парсит турнирную таблицу volley.ru.
        Возвращает DataFrame с колонками: Команда, Сеты, Мячи, Матчи.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки: {e}"

        soup = BeautifulSoup(response.text, 'html.parser')
        # Ищем таблицу с классом s-table (основная таблица чемпионата)
        table = soup.find('table', class_='s-table')
        if not table:
            return None, "Таблица не найдена"

        # Ищем строки тела таблицы (после заголовка)
        rows = table.find_all('tr')
        # Пропускаем заголовок, ищем строки с атрибутом data-teamid
        data_rows = [row for row in rows if row.find('td', attrs={'data-teamid': True})]
        if not data_rows:
            # Альтернативный поиск: строки, где есть ссылка на команду
            data_rows = [row for row in rows if row.find('a', href=re.compile(r'/teams/'))]

        teams = []
        sets_list = []
        points_list = []
        matches_list = []

        for row in data_rows:
            # Название команды – первая ячейка, ссылка
            name_cell = row.find('td')
            if not name_cell:
                continue
            link = name_cell.find('a')
            if link:
                team = link.get_text(strip=True)
            else:
                team = name_cell.get_text(strip=True)
            if not team:
                continue

            # Все ячейки строки
            cells = row.find_all('td')
            if len(cells) < 10:
                continue

            # Сеты – обычно в предпоследней ячейке (перед очками)
            # На странице формат "87:24"
            sets_cell = cells[-2].get_text(strip=True) if len(cells) >= 2 else ''
            if ':' not in sets_cell:
                # Возможно, сеты в другой позиции (индекс -3)
                sets_cell = cells[-3].get_text(strip=True) if len(cells) >= 3 else ''
            if ':' in sets_cell:
                sets_list.append(sets_cell)
            else:
                sets_list.append('0:0')

            # Очки – в последней ячейке, формат "2655:2259"
            points_cell = cells[-1].get_text(strip=True) if cells else ''
            if ':' in points_cell:
                points_list.append(points_cell)
            else:
                points_list.append('0:0')

            # Количество матчей – ищем ячейку с заголовком "И" или просто находим число
            # Обычно это ячейка перед сетами или после побед/поражений
            matches = None
            # Ищем по тексту "И" в заголовках, но проще: в строке есть несколько чисел,
            # одно из них – количество матчей. В таблице volley.ru порядок колонок:
            # Команда, №, далее счета по турам (много), затем И, В, П, Оч, Пар (сеты), (очки)
            # Нам нужно найти число, которое находится между столбцами с результатами и сетами.
            # Упрощённо: ищем все числа в строке, берём первое после названия команды.
            # Но надёжнее – найти ячейку, которая находится перед ячейкой сетов.
            # В текущей версии сайта колонка "И" находится за несколько ячеек до сетов.
            # Пройдём по всем ячейкам, найдём ту, где текст – число, и она не содержит ':'
            for i, cell in enumerate(cells):
                text = cell.get_text(strip=True)
                if text.isdigit() and int(text) >= 1 and int(text) <= 50:
                    # Это потенциально количество матчей
                    matches = int(text)
                    break
            matches_list.append(matches)
            teams.append(team)

        if not teams:
            return None, "Не удалось извлечь команды"

        df = pd.DataFrame({
            'Команда': teams,
            'Сеты': sets_list,
            'Мячи': points_list,
            'Матчи': matches_list
        })
        return df, None
