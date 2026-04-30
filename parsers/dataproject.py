import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urljoin, urlparse
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        if combine_phases:
            phase_containers = soup.find_all('div', class_='rmpView')
            if not phase_containers:
                phase_containers = soup.find_all('div', id=re.compile(r'Content_Main_\d+'))
            combined = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})
            for container in phase_containers:
                phase_stats = self._parse_standings_from_container(container)
                for team, data in phase_stats.items():
                    combined[team]['sets_won'] += data['sets_won']
                    combined[team]['sets_lost'] += data['sets_lost']
                    combined[team]['points_won'] += data['points_won']
                    combined[team]['points_lost'] += data['points_lost']
            stats = combined
        else:
            stats = self._parse_standings_from_container(soup)

        df = self._make_dataframe(stats)
        return df, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        """Ищет страницу матчей (CompetitionMatches.aspx) и парсит матчи между team1 и team2."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Пытаемся найти ссылку на страницу матчей
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        # Ищем в главном меню ссылку на "Matches" или "CompetitionMatches.aspx"
        matches_url = None
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if 'CompetitionMatches.aspx' in href or 'Matches' in link.get_text():
                matches_url = urljoin(base, href)
                break
        if not matches_url:
            # Если не нашли, пробуем подставить стандартный URL
            # Обычно он строится как CompetitionMatches.aspx?ID=...&PID=...
            # Извлечём ID и PID из текущего URL
            import re
            id_match = re.search(r'ID=(\d+)', url)
            pid_match = re.search(r'PID=(\d+)', url)
            if id_match:
                base_match = f"{base}/CompetitionMatches.aspx?ID={id_match.group(1)}"
                if pid_match:
                    base_match += f"&PID={pid_match.group(1)}"
                matches_url = base_match
        if not matches_url:
            return pd.DataFrame()

        # Получаем страницу матчей
        resp_matches = requests.get(matches_url, headers=headers)
        soup_m = BeautifulSoup(resp_matches.text, 'html.parser')
        # Ищем таблицу матчей (обычно RadGrid с классом rgMasterTable)
        matches_table = soup_m.find('table', class_='rgMasterTable')
        if not matches_table:
            return pd.DataFrame()
        rows = matches_table.find_all('tr', class_='rgRow') + matches_table.find_all('tr', class_='rgAltRow')
        head_to_head = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            # Клетки: дата, время, команда1, команда2, счёт, статистика
            home = cells[2].get_text(strip=True)
            away = cells[3].get_text(strip=True)
            if (home == team1 and away == team2) or (home == team2 and away == team1):
                date = cells[0].get_text(strip=True)
                score_cell = cells[4].get_text(strip=True)
                head_to_head.append({
                    'Дата': date,
                    'Хозяева': home,
                    'Гости': away,
                    'Счёт': score_cell
                })
        return pd.DataFrame(head_to_head)

    def _parse_standings_from_container(self, container):
        table = container.find('table', class_='RG_Standing_Main')
        if not table:
            table = container.find('table', class_='rgMasterTable')
        if not table:
            return {}
        return self._parse_standings_table(table)

    def _parse_standings_table(self, table):
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
            s_w = row.find('span', id='SetsWon')
            s_l = row.find('span', id='SetsLost')
            p_w = row.find('span', id='PuntiFatti') or row.find('span', id='PointsWon')
            p_l = row.find('span', id='PuntiSubiti') or row.find('span', id='PointsLost')
            if s_w and s_l:
                try:
                    sets_won = int(s_w.get_text(strip=True))
                    sets_lost = int(s_l.get_text(strip=True))
                except: pass
            if p_w and p_l:
                try:
                    points_won = int(p_w.get_text(strip=True))
                    points_lost = int(p_l.get_text(strip=True))
                except: pass
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
