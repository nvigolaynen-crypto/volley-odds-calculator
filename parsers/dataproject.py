import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
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
        """Ищет личные встречи на странице CompetitionMatches.aspx."""
        # Очищаем названия команд
        team1 = team1.strip()
        team2 = team2.strip()

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        competition_id = query_params.get('ID', [None])[0]
        phase_id = query_params.get('PID', [None])[0]

        if not competition_id:
            return pd.DataFrame()

        # Формируем URL страницы матчей (с PID и без)
        base_path = parsed.path.replace('CompetitionStandings.aspx', 'CompetitionMatches.aspx')
        if base_path == parsed.path:
            base_path = "/CompetitionMatches.aspx"

        # Вариант 1: с PID
        query1 = {}
        if competition_id:
            query1['ID'] = competition_id
        if phase_id:
            query1['PID'] = phase_id
        matches_url1 = urlunparse((parsed.scheme, parsed.netloc, base_path, '', urlencode(query1), ''))

        # Вариант 2: без PID
        query2 = {'ID': competition_id}
        matches_url2 = urlunparse((parsed.scheme, parsed.netloc, base_path, '', urlencode(query2), ''))

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        for matches_url in [matches_url1, matches_url2]:
            try:
                resp = requests.get(matches_url, headers=headers, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                matches_table = self._find_matches_table(soup)
                if matches_table:
                    head_to_head = self._extract_head_to_head(matches_table, team1, team2)
                    if head_to_head:
                        return pd.DataFrame(head_to_head)
            except Exception as e:
                print(f"Ошибка при загрузке {matches_url}: {e}")
                continue

        return pd.DataFrame()

    def _find_matches_table(self, soup):
        # Ищем таблицу матчей по разным классам
        for selector in ['table.rgMasterTable', 'table.RadGrid', 'table.rgDataTable', 'table.rgTable']:
            table = soup.select_one(selector)
            if table:
                return table
        # Если ничего не нашли, ищем любую таблицу, содержащую ключевые слова
        for table in soup.find_all('table'):
            if table.find('th') and any(term in table.get_text() for term in ['Date', 'Team', 'Score', 'Result']):
                return table
        return None

    def _extract_head_to_head(self, table, team1, team2):
        rows = table.find_all('tr', class_='rgRow') + table.find_all('tr', class_='rgAltRow')
        if not rows:
            rows = table.find_all('tr')[1:]  # пропускаем заголовок
        head_to_head = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            try:
                # Объединяем дату и время, если они в разных колонках
                date = cells[0].get_text(strip=True)
                if len(cells) > 5 and cells[1].get_text(strip=True).replace(':', '').isdigit():
                    time = cells[1].get_text(strip=True)
                    date = f"{date} {time}"
                home_team = cells[2].get_text(strip=True)
                away_team = cells[3].get_text(strip=True)
                score = cells[4].get_text(strip=True)
                if (home_team == team1 and away_team == team2) or (home_team == team2 and away_team == team1):
                    head_to_head.append({
                        'Дата': date,
                        'Хозяева': home_team,
                        'Гости': away_team,
                        'Счёт': score
                    })
            except IndexError:
                continue
        return head_to_head

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
