import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Ищем таблицу с результатами (чаще всего класс RG_Standing_Main или rgMasterTable)
        table = soup.find('table', class_='RG_Standing_Main')
        if not table:
            table = soup.find('table', class_='rgMasterTable')
        if not table:
            # Попробуем найти любую таблицу с классом, содержащим 'stand' или 'ranking'
            table = soup.find('table', class_=re.compile(r'(?i)stand|ranking|result'))
        if not table:
            raise ValueError("Не найдена таблица с результатами")

        # Извлекаем заголовки, чтобы понять, где какие данные
        headers = []
        thead = table.find('thead')
        if thead:
            header_cells = thead.find_all('th')
            for th in header_cells:
                headers.append(th.get_text(strip=True))
        # Если заголовков нет, будем ориентироваться по индексам

        # Ищем строки тела таблицы
        tbody = table.find('tbody')
        if not tbody:
            tbody = table
        rows = tbody.find_all('tr')

        stats = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            # Первая ячейка - название команды (может быть внутри <a>)
            team_cell = cells[0]
            team_name = team_cell.get_text(strip=True)
            if not team_name:
                # возможно название в ссылке
                link = team_cell.find('a')
                if link:
                    team_name = link.get_text(strip=True)
            if not team_name:
                continue

            # Поиск сетов и очков – обычно сеты идут до очков, но порядок может быть разным
            # Попробуем найти ячейки по тексту заголовка или по индексу
            sets_won = sets_lost = points_won = points_lost = 0

            # Ищем в строке элементы, которые могут содержать цифры, соответствующие сетами
            # Также ищем по id или class, если они есть
            sets_won_span = row.find('span', id='SetsWon') or row.find('span', class_=re.compile(r'sets.?won', re.I))
            sets_lost_span = row.find('span', id='SetsLost') or row.find('span', class_=re.compile(r'sets.?lost', re.I))
            points_won_span = row.find('span', id='PuntiFatti') or row.find('span', id='PointsWon') or row.find('span', class_=re.compile(r'points.?won', re.I))
            points_lost_span = row.find('span', id='PuntiSubiti') or row.find('span', id='PointsLost') or row.find('span', class_=re.compile(r'points.?lost', re.I))

            if sets_won_span and sets_lost_span:
                try:
                    sets_won = int(sets_won_span.get_text(strip=True))
                    sets_lost = int(sets_lost_span.get_text(strip=True))
                except:
                    pass
            if points_won_span and points_lost_span:
                try:
                    points_won = int(points_won_span.get_text(strip=True))
                    points_lost = int(points_lost_span.get_text(strip=True))
                except:
                    pass

            # Если не нашли по span, пробуем по индексам (предполагаем, что после 2-3 колонок идут сеты и очки)
            if sets_won == 0 and sets_lost == 0 and len(cells) >= 6:
                # Примерный порядок: команда, ... , сеты_выиграно, сеты_проиграно, очки_забито, очки_пропущено
                # Проверим несколько вариантов
                for i in range(1, len(cells)-1):
                    cell_text = cells[i].get_text(strip=True)
                    if cell_text.isdigit():
                        # может быть это сеты
                        if i+1 < len(cells) and cells[i+1].get_text(strip=True).isdigit():
                            sets_won = int(cell_text)
                            sets_lost = int(cells[i+1].get_text(strip=True))
                            break
                if sets_won == 0:
                    # поищем в последних колонках очки
                    for i in range(len(cells)-3, len(cells)):
                        if i+1 < len(cells):
                            try:
                                points_won = int(cells[i].get_text(strip=True))
                                points_lost = int(cells[i+1].get_text(strip=True))
                            except:
                                pass

            # Если сеты и очки не найдены, пропускаем команду
            if sets_won == 0 and sets_lost == 0:
                continue

            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }

        if not stats:
            # Попробуем извлечь данные из всех span с числами (альтернативный метод)
            # Здесь можно сделать более агрессивный поиск, но для простоты выдадим ошибку
            raise ValueError("Не удалось извлечь статистику для команд")

        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()
