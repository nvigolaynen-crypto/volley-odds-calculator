import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    # ------------------------------------------------------------
    # Основной метод парсинга статистики (сеты и мячи)
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # Метод для поиска личных встреч (на странице CompetitionMatches.aspx)
    # ------------------------------------------------------------
    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        team1_norm = self._normalize_team_name(team1)
        team2_norm = self._normalize_team_name(team2)
        print(f"[DEBUG] Поиск личных встреч: {team1_norm} vs {team2_norm} на {url}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # Если передан URL страницы standings, преобразуем его в URL матчей
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

        try:
            response = requests.get(matches_url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Ошибка загрузки страницы матчей: {e}")
            return pd.DataFrame()

        html_text = response.text
        # Компилируем регулярные выражения для поиска матчей (дата, команды, счёт)
        pattern = re.compile(
            rf'(\d{{2}}/\d{{2}}/\d{{4}}).*?{re.escape(team1_norm)}.*?{re.escape(team2_norm)}.*?(\d+)\s*-\s*(\d+)',
            re.DOTALL | re.IGNORECASE
        )
        alt_pattern = re.compile(
            rf'(\d{{2}}/\d{{2}}/\d{{4}}).*?{re.escape(team2_norm)}.*?{re.escape(team1_norm)}.*?(\d+)\s*-\s*(\d+)',
            re.DOTALL | re.IGNORECASE
        )

        matches = []
        for m in pattern.finditer(html_text):
            date, home_score, away_score = m.groups()
            matches.append({
                'Дата': date,
                'Хозяева': team1,
                'Гости': team2,
                'Счёт': f'{home_score}:{away_score}'
            })
        for m in alt_pattern.finditer(html_text):
            date, away_score, home_score = m.groups()
            matches.append({
                'Дата': date,
                'Хозяева': team2,
                'Гости': team1,
                'Счёт': f'{home_score}:{away_score}'
            })

        if not matches:
            print("[DEBUG] Личные встречи не найдены.")
            return pd.DataFrame()
        print(f"[DEBUG] Найдено личных встреч: {len(matches)}")
        return pd.DataFrame(matches)

    def _normalize_team_name(self, name: str) -> str:
        return name.strip().lower()

    # ------------------------------------------------------------
    # Вспомогательные методы для парсинга турнирной таблицы
    # ------------------------------------------------------------
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
