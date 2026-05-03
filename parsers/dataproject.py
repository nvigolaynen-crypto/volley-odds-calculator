import re
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import pandas as pd
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {'User-Agent': 'Mozilla/5.0'}
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
        t1 = team1.strip().lower()
        t2 = team2.strip().lower()
        print(f"[DEBUG] Поиск встреч: {t1} vs {t2}")

        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            print(f"[DEBUG] Статус: {resp.status_code}, длина: {len(resp.text)}")
            # Выводим фрагмент HTML для отладки (первые 3000 символов, чтобы увидеть таблицу)
            print(f"[DEBUG] HTML фрагмент: {resp.text[:3000]}")
        except Exception as e:
            print(f"[DEBUG] Ошибка: {e}")
            return pd.DataFrame()

        html = resp.text
        # Ищем строки с датами и матчами. Формат: DD/MM/YYYY ... Команда1 X - Y Команда2
        # Пример: "11/10/2025 16:00 FC Porto 3 - 0 Clube Kairós"
        # Создадим регулярное выражение, которое захватывает дату, названия команд и два числа
        pattern = re.compile(
            rf'(\d{{2}}/\d{{2}}/\d{{4}})[^\n]*?({re.escape(t1)})[^\n]*?({re.escape(t2)})[^\n]*?(\d+)\s*[-–:]\s*(\d+)',
            re.IGNORECASE
        )
        alt_pattern = re.compile(
            rf'(\d{{2}}/\d{{2}}/\d{{4}})[^\n]*?({re.escape(t2)})[^\n]*?({re.escape(t1)})[^\n]*?(\d+)\s*[-–:]\s*(\d+)',
            re.IGNORECASE
        )

        matches = []
        for m in pattern.finditer(html):
            date, home, away, home_score, away_score = m.groups()
            matches.append({
                'Дата': date,
                'Хозяева': home,
                'Гости': away,
                'Счёт': f"{home_score}:{away_score}"
            })
        for m in alt_pattern.finditer(html):
            date, away, home, away_score, home_score = m.groups()
            matches.append({
                'Дата': date,
                'Хозяева': home,
                'Гости': away,
                'Счёт': f"{home_score}:{away_score}"
            })

        # Если ничего не найдено, попробуем более грубый поиск: ищем любую строку, содержащую дату и оба названия команд
        if not matches:
            print("[DEBUG] Не найдено по основному шаблону, пробуем упрощённый поиск")
            lines = html.split('\n')
            for line in lines:
                if re.search(r'\d{2}/\d{2}/\d{4}', line) and re.search(re.escape(t1), line, re.I) and re.search(re.escape(t2), line, re.I):
                    # Извлекаем счёт из этой строки
                    score_match = re.search(r'(\d+)\s*[-–:]\s*(\d+)', line)
                    if score_match:
                        hs, aws = score_match.groups()
                        # Определяем, какая команда хозяин (можно просто сохранить порядок как в строке)
                        # Попробуем найти сразу после даты
                        # Для простоты запишем обе команды в том порядке, в котором они встретились
                        # Но лучше использовать альтернативный подход
                        parts = re.split(r'\s+', line)
                        # Найдём индексы команд
                        try:
                            idx1 = next(i for i, p in enumerate(parts) if t1 in p.lower())
                            idx2 = next(i for i, p in enumerate(parts) if t2 in p.lower())
                            if idx1 < idx2:
                                home = parts[idx1]
                                away = parts[idx2]
                            else:
                                home = parts[idx2]
                                away = parts[idx1]
                            matches.append({
                                'Дата': re.search(r'(\d{2}/\d{2}/\d{4})', line).group(1),
                                'Хозяева': home,
                                'Гости': away,
                                'Счёт': f"{hs}:{aws}"
                            })
                        except StopIteration:
                            pass

        # Удаляем дубликаты
        seen = set()
        unique = []
        for m in matches:
            key = (m['Дата'], m['Хозяева'], m['Гости'])
            if key not in seen:
                seen.add(key)
                unique.append(m)

        print(f"[DEBUG] Найдено уникальных встреч: {len(unique)}")
        return pd.DataFrame(unique)

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
