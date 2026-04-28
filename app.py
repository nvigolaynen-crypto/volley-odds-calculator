from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from collections import defaultdict
from urllib.parse import urlparse, urljoin

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Глобальные кэши для матчей (в реальном приложении лучше использовать БД)
matches_cache = {}

# ------------------------------------------------------------
# Универсальная функция для получения URL календаря
# ------------------------------------------------------------
def guess_calendar_url(url, league_type):
    """Пытается по URL таблицы построить URL календаря/результатов"""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path
    if 'dataproject.com' in url:
        # Пример: CompetitionStandings.aspx -> CompetitionMatches.aspx
        return url.replace('Standings', 'Matches')
    if 'legavolley.it' in url:
        # classifica/?IdCampionato=xxx -> calendario/?IdCampionato=xxx
        if 'classifica' in path:
            return url.replace('classifica', 'calendario')
        # также можно попробовать /risultati/
    if 'legavolleyfemminile.it' in url:
        if 'classifica' in path:
            return url.replace('classifica', 'calendario')
    if 'tvf.org.tr' in url:
        # /lig/kadinlar-1-ligi -> /lig/kadinlar-1-ligi?sekme=fikstur
        if '?' in url:
            return url + '&sekme=fikstur'
        else:
            return url + '?sekme=fikstur'
    if 'tauronliga.pl' in url:
        # /table.html -> /games.html
        return url.replace('table.html', 'games.html')
    if 'volley.ru' in url:
        if 'predvaritelnyy' in path:
            return url.replace('predvaritelnyy', 'allgames')
        if 'current' in path:
            return url.replace('current', 'allgames')
    return None

# ------------------------------------------------------------
# Функции парсинга календарей для разных лиг
# ------------------------------------------------------------
def parse_volleyru_games(html):
    soup = BeautifulSoup(html, 'html.parser')
    matches = []
    rows = soup.find_all('tr', class_=re.compile(r'table-game'))
    for row in rows:
        team_cells = row.find_all('td')
        if len(team_cells) < 3:
            continue
        home_team = None
        away_team = None
        for i, cell in enumerate(team_cells):
            text = cell.get_text(strip=True)
            if text and text != ':' and home_team is None:
                home_team = text.split(' (')[0]
            elif text and text != ':' and away_team is None:
                away_team = text.split(' (')[0]
                break
        if not home_team or not away_team:
            continue
        scores_cell = row.find('td', class_='s-table__total-score')
        if not scores_cell:
            continue
        total = scores_cell.get_text(strip=True)
        if ':' not in total:
            continue
        home_sets, away_sets = map(int, total.split(':'))
        rounds_cell = row.find('td', class_='s-table__rounds-score')
        home_points = away_points = 0
        if rounds_cell:
            rounds_text = rounds_cell.get_text(strip=True)
            pairs = re.findall(r'(\d+):(\d+)', rounds_text)
            home_points = sum(int(p[0]) for p in pairs)
            away_points = sum(int(p[1]) for p in pairs)
        matches.append({
            'home': home_team,
            'away': away_team,
            'home_sets': home_sets,
            'away_sets': away_sets,
            'home_points': home_points,
            'away_points': away_points
        })
    return matches

def parse_legavolley_games(html):
    soup = BeautifulSoup(html, 'html.parser')
    matches = []
    # Ищем таблицу с классом "table" и id "GareGiornata" (пример)
    table = soup.find('table', id='GareGiornata')
    if not table:
        return matches
    rows = table.find_all('tr', class_=re.compile(r'EvenRow'))
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        # Названия команд в первых двух ячейках (с учётом ссылок)
        home_cell = cols[0]
        away_cell = cols[1]
        home_team = home_cell.get_text(strip=True).split('\n')[0].strip()
        away_team = away_cell.get_text(strip=True).split('\n')[0].strip()
        # Счёт обычно в 3-й ячейке
        score_cell = cols[2].get_text(strip=True)
        if '-' in score_cell or ':' in score_cell:
            score_parts = re.split(r'[-:]', score_cell)
            if len(score_parts) >= 2:
                home_sets = int(score_parts[0])
                away_sets = int(score_parts[1])
            else:
                continue
        else:
            continue
        # Очки (малые) – если есть в дополнительных ячейках
        home_points = away_points = 0
        # В LegaVolley очки по партиям не всегда доступны, но можем попробовать
        matches.append({
            'home': home_team,
            'away': away_team,
            'home_sets': home_sets,
            'away_sets': away_sets,
            'home_points': home_points,
            'away_points': away_points
        })
    return matches

def parse_legavolley_femminile_games(html):
    # Аналогично parse_legavolley_games
    return parse_legavolley_games(html)

def parse_tvf_games(html):
    soup = BeautifulSoup(html, 'html.parser')
    matches = []
    # На TVF календарь подгружается через Livewire, но в HTML уже может быть
    # Попробуем найти секцию с классом "fixture"
    fixture_div = soup.find('div', class_='fixture')
    if not fixture_div:
        return matches
    items = fixture_div.find_all('div', class_='item')
    for item in items:
        home_span = item.find('span', class_='team-home')
        away_span = item.find('span', class_='team-away')
        if not home_span or not away_span:
            continue
        home_team = home_span.get_text(strip=True)
        away_team = away_span.get_text(strip=True)
        score_span = item.find('span', class_='score')
        if not score_span:
            continue
        score_text = score_span.get_text(strip=True)
        if '-' in score_text:
            home_sets, away_sets = map(int, score_text.split('-'))
        else:
            continue
        matches.append({
            'home': home_team,
            'away': away_team,
            'home_sets': home_sets,
            'away_sets': away_sets,
            'home_points': 0,
            'away_points': 0
        })
    return matches

def parse_tauronliga_games(html):
    soup = BeautifulSoup(html, 'html.parser')
    matches = []
    # На Tauron Liga календарь на странице games.html
    # Ищем таблицу с классом "table"
    table = soup.find('table', class_='table')
    if not table:
        return matches
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 4:
            continue
        # Обычно названия команд в 1 и 3 колонках
        home_cell = cols[0]
        away_cell = cols[2]
        home_team = home_cell.get_text(strip=True)
        away_team = away_cell.get_text(strip=True)
        score_cell = cols[1].get_text(strip=True)  # индекс может отличаться
        if ':' in score_cell:
            home_sets, away_sets = map(int, score_cell.split(':'))
        else:
            continue
        matches.append({
            'home': home_team,
            'away': away_team,
            'home_sets': home_sets,
            'away_sets': away_sets,
            'home_points': 0,
            'away_points': 0
        })
    return matches

def parse_fpv_dataproject_games(html):
    # DataProject имеет сложную структуру, но мы можем взять данные из таблицы результатов
    soup = BeautifulSoup(html, 'html.parser')
    matches = []
    # Ищем таблицы результатов
    tables = soup.find_all('table', class_='Table_Risultati')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            # Поиск названий команд
            team_cells = [c for c in cells if c.get('class') and 'tdTitoli' in c.get('class')]
            if len(team_cells) < 2:
                continue
            home_team = team_cells[0].get_text(strip=True)
            away_team = team_cells[1].get_text(strip=True)
            # Результат в ячейке с классом "tdRisultati"
            result_cell = row.find('td', class_='tdRisultati')
            if result_cell:
                score_text = result_cell.get_text(strip=True)
                if '-' in score_text:
                    home_sets, away_sets = map(int, score_text.split('-'))
                else:
                    continue
                matches.append({
                    'home': home_team,
                    'away': away_team,
                    'home_sets': home_sets,
                    'away_sets': away_sets,
                    'home_points': 0,
                    'away_points': 0
                })
    return matches

# ------------------------------------------------------------
# Функции для H2H
# ------------------------------------------------------------
def get_h2h_matches(team1, team2, matches):
    return [m for m in matches if (m['home'] == team1 and m['away'] == team2) or (m['home'] == team2 and m['away'] == team1)]

def calculate_h2h_factor(team1, team2, matches):
    h2h = get_h2h_matches(team1, team2, matches)
    if not h2h:
        return 1.0
    total_sets_1 = 0
    total_sets_2 = 0
    total_points_1 = 0
    total_points_2 = 0
    for m in h2h:
        if m['home'] == team1 and m['away'] == team2:
            total_sets_1 += m['home_sets']
            total_sets_2 += m['away_sets']
            total_points_1 += m['home_points']
            total_points_2 += m['away_points']
        else:
            total_sets_1 += m['away_sets']
            total_sets_2 += m['home_sets']
            total_points_1 += m['away_points']
            total_points_2 += m['home_points']
    sets_ratio = (total_sets_1 / max(total_sets_2, 1)) if total_sets_2 > 0 else total_sets_1 + 1
    points_ratio = (total_points_1 / max(total_points_2, 1)) if total_points_2 > 0 else total_points_1 + 1
    return max(0.5, min(2.0, (sets_ratio * points_ratio) ** 0.5))

# ------------------------------------------------------------
# Парсеры таблиц (оставляем как было, но добавляем сбор календаря)
# ------------------------------------------------------------
def parse_fpv_dataproject_table(html, merge_phases=False):
    soup = BeautifulSoup(html, 'html.parser')
    if not merge_phases:
        first_tab = soup.find('div', id='Content_Main_446') or soup.find('div', class_='rmpView')
        if not first_tab:
            return []
        container = first_tab
    else:
        container = soup
    rows = container.find_all('tr', class_=lambda c: c and ('RG_Standing_Main_AltBackColor' in c))
    teams_dict = defaultdict(lambda: {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0})
    for row in rows:
        team_name_span = row.find('span', id='TeamName')
        if not team_name_span:
            continue
        team_name = team_name_span.get_text(strip=True)
        sets_won_span = row.find('span', id='SetsWon')
        sets_lost_span = row.find('span', id='SetsLost')
        sets_won = int(sets_won_span.get_text(strip=True)) if sets_won_span else 0
        sets_lost = int(sets_lost_span.get_text(strip=True)) if sets_lost_span else 0
        points_won_span = row.find('span', id='PuntiFatti')
        points_lost_span = row.find('span', id='PuntiSubiti')
        points_won = int(points_won_span.get_text(strip=True)) if points_won_span else 0
        points_lost = int(points_lost_span.get_text(strip=True)) if points_lost_span else 0
        if merge_phases:
            teams_dict[team_name]['sets_won'] += sets_won
            teams_dict[team_name]['sets_lost'] += sets_lost
            teams_dict[team_name]['points_won'] += points_won
            teams_dict[team_name]['points_lost'] += points_lost
        else:
            teams_dict[team_name] = {'sets_won': sets_won, 'sets_lost': sets_lost, 'points_won': points_won, 'points_lost': points_lost}
    teams = [{'name': n, 'sets_won': s['sets_won'], 'sets_lost': s['sets_lost'], 'points_won': s['points_won'] or None, 'points_lost': s['points_lost'] or None} for n, s in teams_dict.items()]
    teams.sort(key=lambda x: x['sets_won'] / max(x['sets_lost'], 1), reverse=True)
    return teams

def parse_volleyru_table(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='s-table')
    if not table:
        return []
    teams = []
    rows = table.find_all('tr')
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        team_name = cols[0].get_text(strip=True)
        if not team_name:
            continue
        sets_cell = cols[-1].get_text(strip=True)
        if ':' in sets_cell:
            sets_won, sets_lost = map(int, sets_cell.split(':'))
        else:
            sets_won = sets_lost = 0
        # Очки могут быть в data-balls
        points_won = points_lost = None
        if row.get('data-balls'):
            balls = row['data-balls']
            if ':' in balls:
                points_won, points_lost = map(int, balls.split(':'))
        teams.append({'name': team_name, 'sets_won': sets_won, 'sets_lost': sets_lost, 'points_won': points_won, 'points_lost': points_lost})
    # Если очков нет, пытаемся загрузить календарь
    if not any(t['points_won'] for t in teams):
        cal_url = guess_calendar_url(url, 'volley.ru')
        if cal_url:
            try:
                resp = requests.get(cal_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
                if resp.status_code == 200:
                    games = parse_volleyru_games(resp.text)
                    points_map = defaultdict(lambda: {'points_won': 0, 'points_lost': 0})
                    for g in games:
                        points_map[g['home']]['points_won'] += g['home_points']
                        points_map[g['home']]['points_lost'] += g['away_points']
                        points_map[g['away']]['points_won'] += g['away_points']
                        points_map[g['away']]['points_lost'] += g['home_points']
                    for team in teams:
                        if team['name'] in points_map:
                            team['points_won'] = points_map[team['name']]['points_won']
                            team['points_lost'] = points_map[team['name']]['points_lost']
                    # Сохраняем матчи в глобальный кэш
                    matches_cache[url] = games
            except:
                pass
    return teams

def parse_legavolley_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='GareGiornata')
    if not table:
        return []
    teams = []
    rows = table.find_all('tr', id='EvenRow')
    for row in rows:
        name_cell = row.find('td', class_='DettaglioCal')
        if not name_cell:
            continue
        full_text = name_cell.get_text(strip=True)
        match = re.match(r'^\d+\s+(.*)', full_text)
        team_name = match.group(1) if match else full_text
        cells = row.find_all('td')
        if len(cells) < 12:
            continue
        numbers = [int(cell.get_text(strip=True)) for cell in cells if cell.get_text(strip=True).isdigit()]
        sets_won = numbers[-4] if len(numbers) >= 4 else 0
        sets_lost = numbers[-3] if len(numbers) >= 3 else 0
        points_won = numbers[-2] if len(numbers) >= 2 else None
        points_lost = numbers[-1] if len(numbers) >= 1 else None
        teams.append({'name': team_name, 'sets_won': sets_won, 'sets_lost': sets_lost, 'points_won': points_won, 'points_lost': points_lost})
    return teams

def parse_legavolley_femminile_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table classifica')
    if not table:
        return []
    teams = []
    for row in table.find_all('tr'):
        if row.find('th'):
            continue
        name_td = row.find('td', class_=None)
        if not name_td:
            continue
        a_tag = name_td.find('a')
        team_name = a_tag.get_text(strip=True) if a_tag else name_td.get_text(strip=True)
        if not team_name:
            continue
        extended = row.find_all('td', class_='classifica-estesa')
        if len(extended) < 14:
            continue
        sets_won = int(extended[6].get_text(strip=True))
        sets_lost = int(extended[7].get_text(strip=True))
        points_won = int(extended[8].get_text(strip=True))
        points_lost = int(extended[9].get_text(strip=True))
        teams.append({'name': team_name, 'sets_won': sets_won, 'sets_lost': sets_lost, 'points_won': points_won, 'points_lost': points_lost})
    return teams

def parse_tvf_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    wire_div = soup.find('div', {'wire:snapshot': True})
    if not wire_div:
        return []
    snapshot_attr = wire_div.get('wire:snapshot')
    if not snapshot_attr:
        return []
    try:
        snapshot = json.loads(snapshot_attr)
        league_points = snapshot.get('data', {}).get('leaguePoints', [])
        if not league_points:
            return []
        puantablosu = league_points[0].get('puantablosu', [])
        teams = []
        for team_data in puantablosu:
            if isinstance(team_data, list) and team_data:
                team = team_data[0]
            else:
                team = team_data
            name = team.get('TAKIMADI', '')
            if not name:
                continue
            sets_won = int(team.get('A', 0))
            sets_lost = int(team.get('V', 0))
            points_won = int(team.get('ASP', 0)) if team.get('ASP') else None
            points_lost = int(team.get('VSP', 0)) if team.get('VSP') else None
            teams.append({'name': name, 'sets_won': sets_won, 'sets_lost': sets_lost, 'points_won': points_won, 'points_lost': points_lost})
        return teams
    except:
        return []

def parse_tauronliga_table(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='rs-standings-table-1-1')
    if not table:
        return []
    teams = []
    rows = table.find_all('tr', attrs={'data-teamname': True})
    for row in rows:
        team_link = row.find('a', class_='table-teamname')
        if not team_link:
            continue
        team_name = team_link.get_text(strip=True)
        cells = row.find_all('td')
        if len(cells) < 10:
            continue
        sets_won = int(cells[6].get_text(strip=True))
        sets_lost = int(cells[7].get_text(strip=True))
        points_won = int(cells[8].get_text(strip=True))
        points_lost = int(cells[9].get_text(strip=True))
        teams.append({'name': team_name, 'sets_won': sets_won, 'sets_lost': sets_lost, 'points_won': points_won, 'points_lost': points_lost})
    return teams

# ------------------------------------------------------------
# Функция для предзагрузки матчей для всех лиг (для H2H)
# ------------------------------------------------------------
def preload_matches_for_league(url, league_type):
    """Загружает и парсит календарь, возвращает список матчей и сохраняет в кэш"""
    if url in matches_cache:
        return matches_cache[url]
    cal_url = guess_calendar_url(url, league_type)
    if not cal_url:
        return []
    try:
        resp = requests.get(cal_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=30)
        if resp.status_code != 200:
            return []
        html = resp.text
        if 'dataproject.com' in url:
            games = parse_fpv_dataproject_games(html)
        elif 'volley.ru' in url:
            games = parse_volleyru_games(html)
        elif 'legavolley.it' in url:
            games = parse_legavolley_games(html)
        elif 'legavolleyfemminile.it' in url:
            games = parse_legavolley_femminile_games(html)
        elif 'tvf.org.tr' in url:
            games = parse_tvf_games(html)
        elif 'tauronliga.pl' in url:
            games = parse_tauronliga_games(html)
        else:
            games = []
        matches_cache[url] = games
        return games
    except:
        return []

# ------------------------------------------------------------
# Определение парсера таблицы по URL
# ------------------------------------------------------------
def detect_table_parser(url):
    if 'fpv-web.dataproject.com' in url:
        return parse_fpv_dataproject_table
    if 'volley.ru' in url:
        return lambda html, merge=False: parse_volleyru_table(html, url)
    if 'legavolley.it' in url and 'femminile' not in url:
        return parse_legavolley_table
    if 'legavolleyfemminile.it' in url:
        return parse_legavolley_femminile_table
    if 'tvf.org.tr' in url:
        return parse_tvf_table
    if 'tauronliga.pl' in url:
        return parse_tauronliga_table
    return None

# ------------------------------------------------------------
# API
# ------------------------------------------------------------
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/parse', methods=['POST'])
def parse():
    data = request.json
    url = data.get('url')
    merge_phases = data.get('merge_phases', False)

    if not url:
        return jsonify({'error': 'URL не указан'}), 400

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text

        parser = detect_table_parser(url)
        if not parser:
            return jsonify({'error': 'Сайт не поддерживается'}), 400

        if parser == parse_fpv_dataproject_table:
            teams = parser(html, merge_phases)
        else:
            teams = parser(html)

        if not teams:
            return jsonify({'error': 'Не найдены команды в таблице'}), 404

        # Предзагружаем матчи для H2H (для всех лиг)
        games = preload_matches_for_league(url, None)
        # Сохраняем в глобальном словаре матчей для этого URL
        app.config['LAST_MATCHES'] = games

        return jsonify({'success': True, 'teams': teams, 'count': len(teams)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    teams = data.get('teams', [])
    home_name = data.get('home_team')
    away_name = data.get('away_team')
    use_h2h = data.get('use_h2h', False)  # новый параметр

    if not teams:
        return jsonify({'error': 'Команды не найдены, загрузите таблицу'}), 400

    home = next((t for t in teams if t['name'] == home_name), None)
    away = next((t for t in teams if t['name'] == away_name), None)
    if not home or not away:
        return jsonify({'error': 'Команды не найдены'}), 400

    # BT вероятность на основе сетов
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    expected_ratio = home_strength / max(away_strength, 0.01)
    win_prob_bt = expected_ratio / (1 + expected_ratio)
    win_prob_bt = max(0.05, min(0.95, win_prob_bt))

    win_prob_pr = None
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_points_ratio = home['points_won'] / max(home['points_lost'], 1)
        away_points_ratio = away['points_won'] / max(away['points_lost'], 1)
        expected_ratio_pr = home_points_ratio / max(away_points_ratio, 0.01)
        win_prob_pr = expected_ratio_pr / (1 + expected_ratio_pr)
        win_prob_pr = max(0.05, min(0.95, win_prob_pr))

    final_prob = win_prob_pr if win_prob_pr is not None else win_prob_bt

    # H2H коррекция, если включена и есть матчи
    if use_h2h:
        matches = app.config.get('LAST_MATCHES', [])
        if matches:
            h2h_factor = calculate_h2h_factor(home['name'], away['name'], matches)
            final_prob = final_prob * h2h_factor
            final_prob = max(0.05, min(0.95, final_prob))

    home_win_odds = round(1 / final_prob, 2)
    away_win_odds = round(1 / (1 - final_prob), 2)
    recommendation = f"Ставка на {home['name']}" if final_prob > 0.5 else f"Ставка на {away['name']}"
    fair_odds = home_win_odds if final_prob > 0.5 else away_win_odds

    # Фора по очкам (если есть)
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_points_ratio = home['points_won'] / max(home['points_lost'], 1)
        away_points_ratio = away['points_won'] / max(away['points_lost'], 1)
        if home_points_ratio > away_points_ratio:
            favorite = home
            favorite_is_home = True
        else:
            favorite = away
            favorite_is_home = False
        pts_ratio = max(home_points_ratio, away_points_ratio) / min(home_points_ratio, away_points_ratio)
        expected_diff = (pts_ratio - 1) * 22
        expected_diff = max(-18, min(18, expected_diff))
        handicap = round(abs(expected_diff) / 0.5) * 0.5
        handicap = max(0.5, min(20.0, handicap))
        handicap_line = f"{favorite['name']} (фаворит) дома с форой {handicap}" if favorite_is_home else f"{favorite['name']} (фаворит) в гостях с форой -{handicap}"
    else:
        handicap_line = "Нет данных по очкам для расчёта форы"

    return jsonify({
        'success': True,
        'prediction': {
            'home_team': home['name'],
            'away_team': away['name'],
            'home_sets': f"{home['sets_won']}:{home['sets_lost']}",
            'away_sets': f"{away['sets_won']}:{away['sets_lost']}",
            'home_win_odds': home_win_odds,
            'away_win_odds': away_win_odds,
            'handicap_line': handicap_line,
            'recommendation': recommendation,
            'fair_odds': fair_odds
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
