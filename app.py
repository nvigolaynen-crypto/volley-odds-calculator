from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from collections import defaultdict

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# ------------------------------------------------------------
# Утилита для нормализации названий команд (удаляем город в скобках)
# ------------------------------------------------------------
def normalize_team_name(name):
    name = re.sub(r'\s*\([^)]*\)', '', name)
    return name.strip()

# ------------------------------------------------------------
# 1. Парсер для fpv-web.dataproject.com (португальская лига)
# ------------------------------------------------------------
def parse_fpv_dataproject(html, merge_phases=False):
    soup = BeautifulSoup(html, 'html.parser')
    if not merge_phases:
        first_tab = soup.find('div', id='Content_Main_446')
        if not first_tab:
            first_tab = soup.find('div', class_='rmpView')
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
            teams_dict[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }

    teams = []
    for name, stats in teams_dict.items():
        teams.append({
            'name': name,
            'sets_won': stats['sets_won'],
            'sets_lost': stats['sets_lost'],
            'points_won': stats['points_won'] if stats['points_won'] > 0 else None,
            'points_lost': stats['points_lost'] if stats['points_lost'] > 0 else None
        })
    teams.sort(key=lambda x: x['sets_won'] / max(x['sets_lost'], 1), reverse=True)
    return teams


# ------------------------------------------------------------
# 2. Парсер для volley.ru (чемпионат России) – исправленный
# ------------------------------------------------------------
def parse_volleyru(html, url):
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
        raw_name = cols[0].get_text(strip=True)
        team_name = normalize_team_name(raw_name)
        if not team_name:
            continue
        sets_cell = cols[-1].get_text(strip=True)
        if ':' in sets_cell:
            sets_won, sets_lost = map(int, sets_cell.split(':'))
        else:
            sets_won = sets_lost = 0
        points_won = points_lost = None
        if row.get('data-balls'):
            balls = row['data-balls']
            if ':' in balls:
                points_won, points_lost = map(int, balls.split(':'))
        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })
    if not teams:
        return teams

    games = []
    games_table = soup.find('table', class_='s-table s-table--round')
    if not games_table:
        tables = soup.find_all('table', class_='s-table')
        if len(tables) >= 2:
            games_table = tables[1]
    if games_table:
        game_rows = games_table.find_all('tr', class_=re.compile(r'table-game'))
        if not game_rows:
            all_rows = games_table.find_all('tr')
            if len(all_rows) > 2:
                game_rows = all_rows[2:]
        for row in game_rows:
            cells = row.find_all('td')
            if len(cells) < 4:
                continue
            home_team = None
            away_team = None
            for cell in cells:
                text = cell.get_text(strip=True)
                if text and text != ':' and home_team is None and not re.match(r'\d+:\d+', text):
                    home_team = normalize_team_name(text)
                elif text and text != ':' and away_team is None and not re.match(r'\d+:\d+', text):
                    away_team = normalize_team_name(text)
                    if home_team and away_team:
                        break
            if not home_team or not away_team:
                continue
            score_cell = None
            for cell in cells:
                text = cell.get_text(strip=True)
                if re.match(r'^\d+:\d+$', text):
                    score_cell = cell
                    break
            if not score_cell:
                continue
            total = score_cell.get_text(strip=True)
            home_sets, away_sets = map(int, total.split(':'))
            rounds_cell = None
            for cell in cells:
                text = cell.get_text(strip=True)
                if '(' in text and ')' in text and ':' in text:
                    rounds_cell = cell
                    break
            home_points = away_points = 0
            if rounds_cell:
                rounds_text = rounds_cell.get_text(strip=True)
                pairs = re.findall(r'(\d+):(\d+)', rounds_text)
                home_points = sum(int(p[0]) for p in pairs)
                away_points = sum(int(p[1]) for p in pairs)
            games.append({
                'home': home_team,
                'away': away_team,
                'home_sets': home_sets,
                'away_sets': away_sets,
                'home_points': home_points,
                'away_points': away_points
            })

    if games:
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
        app.config['LAST_MATCHES'] = games
    else:
        app.config['LAST_MATCHES'] = []

    return teams


# ------------------------------------------------------------
# 3. Парсер для legavolley.it (итальянская мужская лига)
# ------------------------------------------------------------
def parse_legavolley(html):
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
        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })
    return teams


# ------------------------------------------------------------
# 4. Парсер для legavolleyfemminile.it (итальянская женская лига)
# ------------------------------------------------------------
def parse_legavolley_femminile(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='table classifica')
    if not table:
        return []

    teams = []
    rows = table.find_all('tr')
    for row in rows:
        if row.find('th'):
            continue
        name_td = row.find('td', class_=None)
        if not name_td:
            continue
        a_tag = name_td.find('a')
        team_name = a_tag.get_text(strip=True) if a_tag else name_td.get_text(strip=True)
        if not team_name:
            continue
        extended_cells = row.find_all('td', class_='classifica-estesa')
        if len(extended_cells) < 14:
            continue
        sets_won = int(extended_cells[6].get_text(strip=True))
        sets_lost = int(extended_cells[7].get_text(strip=True))
        points_won = int(extended_cells[8].get_text(strip=True))
        points_lost = int(extended_cells[9].get_text(strip=True))
        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })
    return teams


# ------------------------------------------------------------
# 5. Парсер для tvf.org.tr (турецкая женская лига) – с поддержкой этапов и групп
# ------------------------------------------------------------
def parse_tvf_stages_and_groups(html):
    """Извлекает доступные этапы (тур) и для каждого этапа список групп."""
    soup = BeautifulSoup(html, 'html.parser')
    stage_select = soup.find('select', {'id': 'filterSelectMain'})
    stages = []
    if stage_select:
        for option in stage_select.find_all('option'):
            val = option.get('value')
            text = option.get_text(strip=True)
            if val:
                stages.append({'value': val, 'label': text})
    return stages


def parse_tvf(html, url=None, stage=None, group=None):
    """
    Парсер TVF, принимает выбранный этап и группу.
    Если stage и group заданы, формирует новый URL с параметрами tur и grup.
    """
    if stage and url:
        base_url = url.split('?')[0]
        new_url = f"{base_url}?tur={stage}"
        if group:
            new_url += f"&grup={group}"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(new_url, headers=headers, timeout=30)
            if resp.status_code == 200:
                html = resp.text
        except:
            pass

    soup = BeautifulSoup(html, 'html.parser')

    # Способ 1: wire:snapshot (основной)
    wire_div = soup.find('div', {'wire:snapshot': True})
    if wire_div:
        snapshot_attr = wire_div.get('wire:snapshot')
        if snapshot_attr:
            try:
                snapshot_data = json.loads(snapshot_attr)
                league_points = snapshot_data.get('data', {}).get('leaguePoints', [])
                if league_points:
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
                        sets_won = int(team.get('A', 0)) if team.get('A') else 0
                        sets_lost = int(team.get('V', 0)) if team.get('V') else 0
                        points_won = int(team.get('ASP', 0)) if team.get('ASP') else None
                        points_lost = int(team.get('VSP', 0)) if team.get('VSP') else None
                        teams.append({
                            'name': name,
                            'sets_won': sets_won,
                            'sets_lost': sets_lost,
                            'points_won': points_won,
                            'points_lost': points_lost
                        })
                    if teams:
                        return teams
            except Exception as e:
                print(f"Ошибка парсинга wire:snapshot TVF: {e}")

    # Способ 2: обычная таблица
    table = soup.find('table', class_=re.compile(r'table|standings|puan|ranking'))
    if not table:
        table = soup.find('table')
    if table:
        teams = []
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            team_name = None
            for col in cols[:3]:
                text = col.get_text(strip=True)
                if text and not text.isdigit() and len(text) > 2:
                    team_name = text
                    break
            if not team_name:
                continue
            numbers = []
            for col in cols:
                text = col.get_text(strip=True)
                if text.isdigit():
                    numbers.append(int(text))
                elif ':' in text or ';' in text:
                    parts = re.split(r'[:;]', text)
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        numbers.append(int(parts[0]))
                        numbers.append(int(parts[1]))
            set_numbers = [n for n in numbers if n <= 150]
            if len(set_numbers) >= 2:
                sets_won = set_numbers[0]
                sets_lost = set_numbers[1]
            elif len(set_numbers) == 1:
                sets_won = set_numbers[0]
                sets_lost = 0
            else:
                sets_won = sets_lost = 0
            point_numbers = [n for n in numbers if n > 100]
            points_won = point_numbers[0] if len(point_numbers) > 0 else None
            points_lost = point_numbers[1] if len(point_numbers) > 1 else None
            teams.append({
                'name': team_name,
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            })
        if teams:
            return teams

    return []


# ------------------------------------------------------------
# 6. Парсер для tauronliga.pl (польская женская лига)
# ------------------------------------------------------------
def parse_tauronliga(html):
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
        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })
    return teams


# ------------------------------------------------------------
# Определение парсера по URL
# ------------------------------------------------------------
def detect_parser(html, url):
    if 'fpv-web.dataproject.com' in url:
        return parse_fpv_dataproject
    if 'volley.ru' in url:
        return parse_volleyru
    if 'legavolley.it' in url and 'femminile' not in url:
        return parse_legavolley
    if 'legavolleyfemminile.it' in url:
        return parse_legavolley_femminile
    if 'tvf.org.tr' in url:
        return parse_tvf
    if 'tauronliga.pl' in url:
        return parse_tauronliga
    return None


# ------------------------------------------------------------
# Функции для H2H (личные встречи)
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
    stage = data.get('stage', None)
    group = data.get('group', None)

    if not url:
        return jsonify({'error': 'URL не указан'}), 400

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text

        if 'tvf.org.tr' in url:
            teams = parse_tvf(html, url, stage, group)
        else:
            parser = detect_parser(html, url)
            if not parser:
                return jsonify({'error': 'Сайт не поддерживается'}), 400
            if parser == parse_fpv_dataproject:
                teams = parser(html, merge_phases)
            elif parser == parse_volleyru:
                teams = parser(html, url)
            else:
                teams = parser(html)

        if not teams:
            return jsonify({'error': 'Не найдены команды в таблице'}), 404

        return jsonify({'success': True, 'teams': teams, 'count': len(teams)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tvf/stages', methods=['POST'])
def tvf_stages():
    """Получить доступные этапы для TVF"""
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL не указан'}), 400
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
        stages = parse_tvf_stages_and_groups(html)
        return jsonify({'stages': stages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tvf/groups', methods=['POST'])
def tvf_groups():
    """Получить группы для выбранного этапа TVF"""
    data = request.json
    url = data.get('url')
    stage = data.get('stage')
    if not url or not stage:
        return jsonify({'error': 'Не указан URL или этап'}), 400
    try:
        base_url = url.split('?')[0]
        new_url = f"{base_url}?tur={stage}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(new_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        groups = []
        # Ищем select с id="filterSelect1"
        group_select = soup.find('select', {'id': 'filterSelect1'})
        if group_select:
            for option in group_select.find_all('option'):
                val = option.get('value')
                text = option.get_text(strip=True)
                if val and text and text not in ['Grup Seçiniz', 'Seçiniz', '-- Seçiniz --']:
                    groups.append({'value': val, 'label': text})
        
        # Если не нашли, ищем любой select с опциями-буквами
        if not groups:
            all_selects = soup.find_all('select')
            for sel in all_selects:
                options = sel.find_all('option')
                for opt in options:
                    text = opt.get_text(strip=True)
                    if re.match(r'^[A-ZÇĞİÖŞÜ]{1,2}$', text):
                        for opt2 in options:
                            val2 = opt2.get('value')
                            text2 = opt2.get_text(strip=True)
                            if val2 and text2 and text2 not in ['Grup Seçiniz', 'Seçiniz', '-- Seçiniz --']:
                                groups.append({'value': val2, 'label': text2})
                        break
                if groups:
                    break
        
        # Если всё ещё нет, ищем div с классом, содержащим "grup", и ссылки
        if not groups:
            group_containers = soup.find_all('div', class_=re.compile(r'grup|group', re.I))
            for container in group_containers:
                links = container.find_all('a')
                for link in links:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    if href and ('grup' in href or 'group' in href) and text:
                        match = re.search(r'[?&]grup=([^&]+)', href)
                        if match:
                            groups.append({'value': match.group(1), 'label': text})
                if groups:
                    break
        
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    teams = data.get('teams', [])
    home_name = data.get('home_team')
    away_name = data.get('away_team')
    neutral_ground = data.get('neutral_ground', False)
    use_h2h = data.get('use_h2h', False)

    if not teams:
        return jsonify({'error': 'Команды не найдены, загрузите таблицу'}), 400

    home = next((t for t in teams if t['name'] == home_name), None)
    away = next((t for t in teams if t['name'] == away_name), None)
    if not home or not away:
        return jsonify({'error': 'Команды не найдены'}), 400

    # BT вероятность (на основе сетов)
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    home_adv = 1.05 if not neutral_ground else 1.0
    expected_ratio = (home_strength * home_adv) / max(away_strength, 0.01)
    win_prob_bt = expected_ratio / (1 + expected_ratio)
    win_prob_bt = max(0.05, min(0.95, win_prob_bt))

    # PR вероятность (на основе очков, если есть)
    win_prob_pr = None
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_pts_ratio = home['points_won'] / max(home['points_lost'], 1)
        away_pts_ratio = away['points_won'] / max(away['points_lost'], 1)
        expected_ratio_pr = (home_pts_ratio * home_adv) / max(away_pts_ratio, 0.01)
        win_prob_pr = expected_ratio_pr / (1 + expected_ratio_pr)
        win_prob_pr = max(0.05, min(0.95, win_prob_pr))

    final_prob = win_prob_pr if win_prob_pr is not None else win_prob_bt

    # H2H коррекция
    if use_h2h:
        matches = app.config.get('LAST_MATCHES', [])
        if matches:
            h2h_factor = calculate_h2h_factor(home['name'], away['name'], matches)
            final_prob = final_prob * h2h_factor
            final_prob = max(0.05, min(0.95, final_prob))

    home_win_odds = round(1 / final_prob, 2)
    away_win_odds = round(1 / (1 - final_prob), 2)
    if final_prob > 0.5:
        recommendation = f"Ставка на {home['name']}"
        fair_odds = home_win_odds
    else:
        recommendation = f"Ставка на {away['name']}"
        fair_odds = away_win_odds

    # Фора по очкам
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_pts_ratio = home['points_won'] / max(home['points_lost'], 1)
        away_pts_ratio = away['points_won'] / max(away['points_lost'], 1)
        if home_pts_ratio > away_pts_ratio:
            favorite = home
            favorite_is_home = True
        else:
            favorite = away
            favorite_is_home = False
        pts_ratio = max(home_pts_ratio, away_pts_ratio) / min(home_pts_ratio, away_pts_ratio)
        expected_diff = (pts_ratio - 1) * 22
        expected_diff = max(-18, min(18, expected_diff))
        handicap = round(abs(expected_diff) / 0.5) * 0.5
        handicap = max(0.5, min(20.0, handicap))
        if favorite_is_home:
            handicap_line = f"{favorite['name']} (фаворит) дома с форой {handicap}"
        else:
            handicap_line = f"{favorite['name']} (фаворит) в гостях с форой -{handicap}"
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
