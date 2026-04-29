import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """
        Если combine_phases=True, собирает статистику по всем этапам (вкладкам).
        Иначе только текущая страница.
        """
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
        stats = self._parse_standings_page(soup)
        return stats

    def _fetch_all_phases(self, start_url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(start_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Ищем вкладки этапов (RadTabStrip)
        tab_strip = soup.find('div', class_='RadTabStrip')
        if not tab_strip:
            # Может быть другой класс
            tab_strip = soup.find('ul', class_='rtsUL')
        phase_urls = []
        if tab_strip:
            links = tab_strip.find_all('a')
            for link in links:
                href = link.get('href')
                if href and 'javascript' not in href:
                    full_url = urljoin(start_url, href)
                    if full_url not in phase_urls:
                        phase_urls.append(full_url)
        # Если вкладок не найдено, парсим только текущую страницу
        if not phase_urls:
            phase_urls = [start_url]

        combined_stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                              'points_won': 0, 'points_lost': 0})
        for phase_url in phase_urls:
            phase_stats = self._fetch_single_phase(phase_url)
            for team, data in phase_stats.items():
                combined_stats[team]['sets_won'] += data['sets_won']
                combined_stats[team]['sets_lost'] += data['sets_lost']
                combined_stats[team]['points_won'] += data['points_won']
                combined_stats[team]['points_lost'] += data['points_lost']
        return combined_stats

    def _parse_standings_page(self, soup):
        table = soup.find('table', class_='RG_Standing_Main')
        if not table:
            table = soup.find('table', class_='rgMasterTable')
        if not table:
            raise ValueError("Не найдена таблица с результатами")

        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')
        stats = {}
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            team_cell = cells[0]
            team_name = team_cell.get_text(strip=True)
            if not team_name:
                link = team_cell.find('a')
                if link:
                    team_name = link.get_text(strip=True)
            if not team_name:
                continue

            sets_won = sets_lost = points_won = points_lost = 0

            # Поиск по span с определёнными ID или классами
            sets_won_span = row.find('span', id='SetsWon') or row.find('span', class_=re.compile(r'sets.?won', re.I))
            sets_lost_span = row.find('span', id='SetsLost') or row.find('span', class_=re.compile(r'sets.?lost', re.I))
            points_won_span = row.find('span', id='PuntiFatti') or row.find('span', id='PointsWon')
            points_lost_span = row.find('span', id='PuntiSubiti') or row.find('span', id='PointsLost')

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

            # Эвристика по позициям, если не нашли
            if sets_won == 0 and sets_lost == 0 and len(cells) >= 6:
                for i in range(1, len(cells)-1):
                    if cells[i].get_text(strip=True).isdigit() and cells[i+1].get_text(strip=True).isdigit():
                        sets_won = int(cells[i].get_text(strip=True))
                        sets_lost = int(cells[i+1].get_text(strip=True))
                        break
                for i in range(len(cells)-3, len(cells)-1):
                    try:
                        points_won = int(cells[i].get_text(strip=True))
                        points_lost = int(cells[i+1].get_text(strip=True))
                        break
                    except:
                        pass

            if sets_won == 0 and sets_lost == 0:
                continue

            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
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
