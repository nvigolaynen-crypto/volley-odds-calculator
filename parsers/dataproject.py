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
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
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
        team1_norm = self._normalize_team_name(team1)
        team2_norm = self._normalize_team_name(team2)
        print(f"[DEBUG] Поиск: '{team1_norm}' vs '{team2_norm}'")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Формируем URL матчей
        if 'CompetitionStandings.aspx' in url:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            comp_id = query.get('ID', [None])[0]
            phase_id = query.get('PID', [None])[0]
            if comp_id:
                matches_url = f"{parsed.scheme}://{parsed.netloc}/CompetitionMatches.aspx?ID={comp_id}"
                if phase_id:
                    matches_url += f"&PID={phase_id}"
            else:
                matches_url = url
        else:
            matches_url = url

        print(f"[DEBUG] Загружаем: {matches_url}")
        try:
            response = requests.get(matches_url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка: {e}")
            return pd.DataFrame()

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='rgMasterTable')
        if not table:
            table = soup.find('table', class_='RadGrid')
        if not table:
            print("[DEBUG] Таблица не найдена")
            return pd.DataFrame()

        rows = table.find_all('tr', class_='rgRow') + table.find_all('tr', class_='rgAltRow')
        if not rows:
            rows = table.find_all('tr')[1:]

        # Регулярное выражение для счёта в формате "3 - 0" или "3:0", где числа ≤ 3 (сеты) или ≤ 25 (очки)
        # Но для простоты будем искать два числа, разделённые дефисом/двоеточием, и проверять, что числа не являются годом
        score_pattern = re.compile(r'(\d{1,2})\s*[-–:]\s*(\d{1,2})')
        matches = []
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 5:
                continue
            date_cell = cells[0].get_text(strip=True)
            # Отбираем только даты 2025 или 2026
            if not re.search(r'202[56]', date_cell):
                continue
            home_raw = cells[2].get_text(strip=True)
            away_raw = cells[3].get_text(strip=True)
            # Ячейка со счётом обычно 5-я (индекс 4), но может быть 6-я
            score_cell = cells[4].get_text(strip=True)
            if not score_pattern.search(score_cell) and len(cells) > 5:
                score_cell = cells[5].get_text(strip=True)
            score_match = score_pattern.search(score_cell)
            if not score_match:
                continue
            home_score, away_score = score_match.groups()
            # Если числа большие (например, 2025), пропускаем
            if int(home_score) > 50 or int(away_score) > 50:
                continue
            score = f"{home_score}:{away_score}"
            home_norm = self._normalize_team_name(home_raw)
            away_norm = self._normalize_team_name(away_raw)
            if (home_norm == team1_norm and away_norm == team2_norm) or (home_norm == team2_norm and away_norm == team1_norm):
                matches.append({
                    'Дата': date_cell,
                    'Хозяева': home_raw,
                    'Гости': away_raw,
                    'Счёт': score
                })
        print(f"[DEBUG] Найдено встреч: {len(matches)}")
        return pd.DataFrame(matches)

    def _normalize_team_name(self, name: str) -> str:
        return name.strip().lower()

    # остальные методы (_parse_standings_from_container, _parse_standings_table, _make_dataframe) без изменений
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
