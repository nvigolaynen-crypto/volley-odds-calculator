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
# 2. Парсер для volley.ru (чемпионат России)
# ------------------------------------------------------------
def parse_volleyru(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='s-table')
    if not table:
        return []

    teams = []
    rows = table.find_all('tr')
    for row in rows[1:]:  # пропускаем заголовок
        cols = row.find_all('td')
        if len(cols) < 3:
            continue

        team_name_cell = cols[0]
        team_name = team_name_cell.get_text(strip=True)
        if not team_name:
            continue

        # Сеты из последней колонки (формат "89:31")
        sets_cell = cols[-1].get_text(strip=True)
        sets_parts = sets_cell.split(':')
        if len(sets_parts) == 2:
            try:
                sets_won = int(sets_parts[0])
                sets_lost = int(sets_parts[1])
            except:
                sets_won = 0
                sets_lost = 0
        else:
            sets_won = 0
            sets_lost = 0

        # Очки из data-balls (если есть)
        points_won = None
        points_lost = None
        if row.has_attr('data-balls'):
            balls = row['data-balls']
            if ':' in balls:
                parts = balls.split(':')
                if len(parts) == 2:
                    try:
                        points_won = int(parts[0])
                        points_lost = int(parts[1])
                    except:
                        pass

        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })
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
        if match:
            team_name = match.group(1)
        else:
            team_name = full_text

        cells = row.find_all('td')
        if len(cells) < 12:
            continue

        numbers = []
        for cell in cells:
            text = cell.get_text(strip=True)
            if text.isdigit():
                numbers.append(int(text))

        if len(numbers) >= 4:
            sets_won = numbers[-4] if len(numbers) >= 4 else 0
            sets_lost = numbers[-3] if len(numbers) >= 3 else 0
            points_won = numbers[-2] if len(numbers) >= 2 else None
            points_lost = numbers[-1] if len(numbers) >= 1 else None
        else:
            sets_won = 0
            sets_lost = 0
            points_won = None
            points_lost = None

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
        if a_tag:
            team_name = a_tag.get_text(strip=True)
        else:
            team_name = name_td.get_text(strip=True)
        if not team_name:
            continue

        extended_cells = row.find_all('td', class_='classifica-estesa')
        if len(extended_cells) < 14:
            continue

        try:
            sets_won = int(extended_cells[6].get_text(strip=True))
            sets_lost = int(extended_cells[7].get_text(strip=True))
            points_won = int(extended_cells[8].get_text(strip=True))
            points_lost = int(extended_cells[9].get_text(strip=True))
        except (ValueError, IndexError):
            continue

        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })

    return teams

# ------------------------------------------------------------
# 5. Парсер для tvf.org.tr (турецкая женская лига)
# ------------------------------------------------------------
def parse_tvf(html):
    soup = BeautifulSoup(html, 'html.parser')
    wire_div = soup.find('div', {'wire:snapshot': True})
    if not wire_div:
        return []

    snapshot_attr = wire_div.get('wire:snapshot')
    if not snapshot_attr:
        return []

    try:
        snapshot_data = json.loads(snapshot_attr)
        league_points = snapshot_data.get('data', {}).get('leaguePoints', [])
        if not league_points:
            return []
        puantablosu = league_points[0].get('puantablosu', [])
        if not puantablosu:
            return []

        teams = []
        for team_data in puantablosu:
            if isinstance(team_data, list) and len(team_data) > 0:
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

            teams.append({
                'name': name,
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            })

        return teams
    except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
        print(f"JSON parse error: {e}")
        return []

# ------------------------------------------------------------
# 6. Парсер для tauronliga.pl (польская женская лига)
# ------------------------------------------------------------
def parse_tauronliga(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Ищем таблицу с id "rs-standings-table-1-1"
    table = soup.find('table', id='rs-standings-table-1-1')
    if not table:
        return []

    teams = []
    # Находим все строки с атрибутом data-teamname (это строки команд)
    rows = table.find_all('tr', attrs={'data-teamname': True})
    for row in rows:
        # Извлекаем название команды
        team_link = row.find('a', class_='table-teamname')
        if not team_link:
            continue
        team_name = team_link.get_text(strip=True)
        if not team_name:
            continue

        # Извлекаем все ячейки td
        cells = row.find_all('td')
        if len(cells) < 10:
            continue

        # Индексы: 6 – выигранные сеты, 7 – проигранные сеты,
        # 8 – выигранные очки (малые), 9 – проигранные очки
        try:
            sets_won = int(cells[6].get_text(strip=True))
            sets_lost = int(cells[7].get_text(strip=True))
            points_won = int(cells[8].get_text(strip=True))
            points_lost = int(cells[9].get_text(strip=True))
        except (ValueError, IndexError):
            # Если не удалось, пропускаем команду
            continue

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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text

        parser = detect_parser(html, url)
        if not parser:
            return jsonify({'error': 'Сайт не поддерживается. Напишите разработчику.'}), 400

        if parser == parse_fpv_dataproject:
            teams = parser(html, merge_phases)
        else:
            teams = parser(html)

        if not teams:
            return jsonify({'error': 'Не найдены команды в таблице'}), 404

        return jsonify({'success': True, 'teams': teams, 'count': len(teams)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    teams = data.get('teams', [])
    home_name = data.get('home_team')
    away_name = data.get('away_team')

    home = next((t for t in teams if t['name'] == home_name), None)
    away = next((t for t in teams if t['name'] == away_name), None)
    if not home or not away:
        return jsonify({'error': 'Команды не найдены'}), 400

    # Коэффициенты на победу на основе сетов
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    expected_ratio = home_strength / max(away_strength, 0.01)
    win_prob = expected_ratio / (1 + expected_ratio)
    win_prob = max(0.05, min(0.95, win_prob))

    home_win_odds = round(1 / win_prob, 2)
    away_win_odds = round(1 / (1 - win_prob), 2)

    # Фора по очкам (мячам)
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
            'handicap_line': handicap_line
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
