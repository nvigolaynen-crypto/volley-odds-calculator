import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin
from .base_parser import BaseParser

class RussiaVolleyRuParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        if combine_phases:
            stats = self._fetch_all_phases(url)
        else:
            stats = self._fetch_single_phase(url)
        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def _fetch_single_phase(self, url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        matrix_table = soup.find('table', class_='s-table')
        if not matrix_table or 's-table--round' in matrix_table.get('class', []):
            raise ValueError("Не найдена матричная таблица")
        return self._parse_matrix_table(matrix_table)

    def _fetch_all_phases(self, start_url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(start_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        tabs = soup.find_all('a', class_='vl-tabs__item')
        phase_urls = []
        for tab in tabs:
            href = tab.get('href')
            name = tab.get_text(strip=True)
            if href and name not in ['Все игры', 'Положение', 'Фотографии', 'Статистика']:
                phase_urls.append(urljoin(start_url, href))
        phase_urls = list(dict.fromkeys(phase_urls))

        combined = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})
        for phase_url in phase_urls:
            phase_stats = self._fetch_single_phase(phase_url)
            for team, data in phase_stats.items():
                combined[team]['sets_won'] += data['sets_won']
                combined[team]['sets_lost'] += data['sets_lost']
                combined[team]['points_won'] += data['points_won']
                combined[team]['points_lost'] += data['points_lost']
        return combined

    def _parse_matrix_table(self, table):
        thead = table.find('thead')
        header_row = thead.find('tr')
        ths = header_row.find_all('th')[2:]
        column_numbers = [int(th.get_text(strip=True)) for th in ths if th.get_text(strip=True).isdigit()]

        team_by_num = {}
        stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})

        tbody = table.find('tbody')
        rows = tbody.find_all('tr')

        # Извлекаем названия команд и итоговые очки из data-balls
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            team_name = cells[0].get_text(strip=True).split('(')[0].strip()
            team_num = int(cells[1].get_text(strip=True))
            team_by_num[team_num] = team_name
            last_cell = cells[-1]
            balls = last_cell.get('data-balls')
            if balls and ':' in balls:
                pw, pl = map(int, balls.split(':'))
                stats[team_name]['points_won'] = pw
                stats[team_name]['points_lost'] = pl

        # Извлекаем сеты – теперь ищем как <div>, так и <a>
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            home_num = int(cells[1].get_text(strip=True))
            home_name = team_by_num.get(home_num)
            if not home_name:
                continue
            result_cells = cells[2:-5]   # пропускаем итоговые колонки
            for col_idx, cell in enumerate(result_cells):
                if col_idx >= len(column_numbers):
                    break
                away_num = column_numbers[col_idx]
                away_name = team_by_num.get(away_num)
                if not away_name:
                    continue
                # Ищем все ссылки внутри ячейки – каждая ссылка это результат одного матча
                links = cell.find_all('a')
                if not links:
                    # Если нет ссылок, пробуем div
                    divs = cell.find_all('div')
                    links = divs
                for link in links:
                    score_text = link.get_text(strip=True)
                    match = re.search(r'(\d+):(\d+)', score_text)
                    if match:
                        hs, aws = map(int, match.groups())
                        # Поскольку в ячейке два матча (два круга), порядок может быть разный.
                        # Определить хозяина и гостя сложно, но в матрице в строке home_name
                        # первый результат – матч home vs away, второй – away vs home.
                        # Но мы не знаем, какой из них первый. Однако для суммарной статистики
                        # нам нужно просто добавить сеты обеим командам соответственно.
                        # Простейший способ: добавляем всегда как home vs away, но потом второй матч
                        # добавится как home = away. Это даст правильную сумму.
                        stats[home_name]['sets_won'] += hs
                        stats[home_name]['sets_lost'] += aws
                        stats[away_name]['sets_won'] += aws
                        stats[away_name]['sets_lost'] += hs
                        # Для второго матча (если он есть) порядок сменится, так как второй link
                        # будет означать матч away vs home, но мы уже учли его, так как для обоих
                        # матчей мы добавили обе команды. Однако мы добавляем дважды, если в ячейке два матча.
                        # Поэтому нужно обрабатывать только один матч? Нет, в ячейке два матча, и для каждого нужно добавить.
                        # Но из-за того, что оба матча добавляются одинаково, результат будет удвоенным? Нет, потому что
                        # во втором матче hs и aws поменяны местами. В двухматчевом круге:
                        # матч1: home 3-1 away -> home +3, away +1
                        # матч2: away 3-2 home -> away +3, home +2
                        # Если мы оба раза добавим как home vs away, то получим home +3+2, away +1+3 => правильно.
                        # Значит, можно обрабатывать все ссылки одинаково. Главное – не пропустить ни одной.
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
