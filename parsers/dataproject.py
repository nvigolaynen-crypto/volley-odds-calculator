import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
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
        return self._parse_standings_page(soup)

    def _fetch_all_phases(self, start_url: str):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(start_url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        phase_urls = self._extract_phase_urls(soup, start_url)
        if not phase_urls:
            phase_urls = [start_url]
        combined_stats = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0,
                                              'points_won': 0, 'points_lost': 0})
        for phase_url in phase_urls:
            phase_resp = requests.get(phase_url, headers=headers)
            phase_soup = BeautifulSoup(phase_resp.text, 'html.parser')
            phase_stats = self._parse_standings_page(phase_soup)
            for team, data in phase_stats.items():
                combined_stats[team]['sets_won'] += data['sets_won']
                combined_stats[team]['sets_lost'] += data['sets_lost']
                combined_stats[team]['points_won'] += data['points_won']
                combined_stats[team]['points_lost'] += data['points_lost']
        return combined_stats

    def _extract_phase_urls(self, soup, base_url):
        urls = set()
        # Ищем вкладки RadTabStrip
        tab_strip = soup.find('div', class_='RadTabStrip')
        if tab_strip:
            links = tab_strip.find_all('a', class_='rtsLink')
            for link in links:
                href = link.get('href')
                if href:
                    urls.add(urljoin(base_url, href))
        # Ищем выпадающий список этапов
        phase_select = soup.find('select', {'name': re.compile(r'PhaseSelect', re.I)})
        if phase_select:
            for option in phase_select.find_all('option'):
                value = option.get('value')
                if value and value.isdigit():
                    parsed = urlparse(base_url)
                    query = parse_qs(parsed.query)
                    query['PID'] = [value]
                    new_query = urlencode(query, doseq=True)
                    new_url = urlunparse(parsed._replace(query=new_query))
                    urls.add(new_url)
        return list(urls)

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
            # Поиск по ID
            sets_won_span = row.find('span', id='SetsWon')
            sets_lost_span = row.find('span', id='SetsLost')
            points_won_span = row.find('span', id='PuntiFatti') or row.find('span', id='PointsWon')
            points_lost_span = row.find('span', id='PuntiSubiti') or row.find('span', id='PointsLost')
            if sets_won_span and sets_lost_span:
                try:
                    sets_won = int(sets_won_span.get_text(strip=True))
                    sets_lost = int(sets_lost_span.get_text(strip=True))
                except: pass
            if points_won_span and points_lost_span:
                try:
                    points_won = int(points_won_span.get_text(strip=True))
                    points_lost = int(points_lost_span.get_text(strip=True))
                except: pass
            # Если не нашли, пробуем эвристику по индексам
            if sets_won == 0 and len(cells) >= 6:
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
                    except: pass
            if sets_won == 0 and sets_lost == 0:
                continue
            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }
        if not stats:
            raise ValueError("Не удалось извлечь статистику для команд")
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
