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
        team1_norm = team1.strip().lower()
        team2_norm = team2.strip().lower()
        print(f"[DEBUG] Поиск личных встреч: {team1_norm} vs {team2_norm}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        parsed = urlparse(url)
        competition_id = parse_qs(parsed.query).get('ID', [None])[0]
        phase_id = parse_qs(parsed.query).get('PID', [None])[0]

        # Формируем возможные URL страницы матчей
        urls_to_try = []
        if competition_id:
            base = f"{parsed.scheme}://{parsed.netloc}/CompetitionMatches.aspx?ID={competition_id}"
            urls_to_try.append(base)
            if phase_id:
                urls_to_try.append(f"{base}&PID={phase_id}")
        if 'CompetitionMatches.aspx' in url:
            urls_to_try.append(url)

        for matches_url in urls_to_try:
            print(f"[DEBUG] Пробуем URL: {matches_url}")
            try:
                resp = requests.get(matches_url, headers=headers, timeout=10)
                print(f"[DEBUG] Статус: {resp.status_code}")
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Ищем таблицу с матчами
                table = self._find_matches_table(soup)
                if not table:
                    print("[DEBUG] Таблица матчей не найдена")
                    continue
                matches = self._extract_head_to_head(table, team1_norm, team2_norm)
                if matches:
                    print(f"[DEBUG] Найдено {len(matches)} матчей")
                    return pd.DataFrame(matches)
            except Exception as e:
                print(f"[DEBUG] Ошибка: {e}")
                continue

        print("[DEBUG] Личные встречи не найдены")
        return pd.DataFrame()

    def _find_matches_table(self, soup):
        # Пробуем найти таблицу по классам
        for selector in ['table.rgMasterTable', 'table.RadGrid', 'table.rgDataTable', 'table.rgTable']:
            table = soup.select_one(selector)
            if table:
                return table
        # Ищем любую таблицу, содержащую строки с классом rgRow или rgAltRow
        for table in soup.find_all('table'):
            if table.find('tr', class_='rgRow') or table.find('tr', class_='rgAltRow'):
                return table
            # Если есть заголовок с колонками Date, Team, Score
            header_row = table.find('tr')
            if header_row and any(cell.get_text() in ['Date', 'Team', 'Score', 'Result'] for cell in header_row.find_all('th')):
                return table
        return None

    def _extract_head_to_head(self, table, team1_norm, team2_norm):
        rows = table.find_all('tr', class_='rgRow') + table.find_all('tr', class_='rgAltRow')
        if not rows:
            rows = table.find_all('tr')[1:]  # пропускаем первую строку (заголовок)
        matches = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            try:
                date = cells[0].get_text(strip=True)
                if len(cells) > 5 and ':' in cells[1].get_text(strip=True):
                    date += " " + cells[1].get_text(strip=True)
                home = cells[2].get_text(strip=True).lower()
                away = cells[3].get_text(strip=True).lower()
                score = cells[4].get_text(strip=True)
                if (home == team1_norm and away == team2_norm) or (home == team2_norm and away == team1_norm):
                    matches.append({
                        'Дата': date,
                        'Хозяева': cells[2].get_text(strip=True),
                        'Гости': cells[3].get_text(strip=True),
                        'Счёт': score
                    })
            except IndexError:
                continue
        return matches

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
