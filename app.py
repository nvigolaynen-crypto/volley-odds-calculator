from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

def parse_portuguese_table(soup):
    """Специальный парсер для португальской таблицы (DataProject)"""
    # Ищем таблицу с классом grid
    table = soup.find('table', class_=re.compile(r'grid'))
    if not table:
        return []
    
    teams = []
    rows = table.find_all('tr')
    
    # Пропускаем заголовок
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) < 10:
            continue
        
        # Название команды - обычно 1-я колонка
        team_name = cols[0].get_text().strip()
        if not team_name:
            team_name = cols[1].get_text().strip()
        
        if not team_name:
            continue
        
        # Португальская таблица имеет фиксированные индексы:
        # Индексы с 0:
        # 0 - место, 1 - команда, 2 - игры, 3 - победы, 4 - поражения,
        # 5 - сеты выиграно, 6 - сеты проиграно,
        # 7 - очки выиграно, 8 - очки проиграно, ...
        # По скрину 13: сеты (61,12) находятся в 5 и 6 колонках, очки (1772,1336) в 7 и 8.
        
        try:
            sets_won = int(cols[5].get_text().strip())
            sets_lost = int(cols[6].get_text().strip())
            points_won = int(cols[7].get_text().strip())
            points_lost = int(cols[8].get_text().strip())
        except (ValueError, IndexError):
            # Если не получилось - пробуем другие индексы
            continue
        
        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })
    
    return teams

def parse_generic_table(html):
    """Универсальный парсер для других сайтов"""
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    
    for table in tables:
        teams = []
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            
            # Название команды
            team_name = None
            for col in cols[:3]:
                text = col.get_text().strip()
                if text and not text.isdigit() and len(text) > 1:
                    team_name = text
                    break
            if not team_name:
                continue
            
            # Собираем числа
            numbers = []
            for col in cols:
                text = col.get_text().strip()
                nums = re.findall(r'\b(\d+)\b', text)
                for num in nums:
                    n = int(num)
                    if n < 5000:
                        numbers.append(n)
            
            # Разделяем на сеты (маленькие) и очки (большие)
            small = [n for n in numbers if n <= 150]
            large = [n for n in numbers if n > 500]
            
            sets_won = small[0] if len(small) > 0 else 0
            sets_lost = small[1] if len(small) > 1 else 0
            points_won = large[0] if len(large) > 0 else None
            points_lost = large[1] if len(large) > 1 else None
            
            teams.append({
                'name': team_name,
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            })
        
        if len(teams) >= 2:
            return teams
    
    return []

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/parse', methods=['POST'])
def parse():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL не указан'}), 400
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Определяем сайт по URL
        if 'dataproject.com' in url.lower():
            teams = parse_portuguese_table(soup)
        else:
            teams = parse_generic_table(response.text)
        
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
    
    # Единый расчёт: используем очки, если они есть, иначе сеты
    use_points = home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0
    
    if use_points:
        home_strength = home['points_won'] / max(home['points_lost'], 1)
        away_strength = away['points_won'] / max(away['points_lost'], 1)
    else:
        home_strength = home['sets_won'] / max(home['sets_lost'], 1)
        away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    
    # Коэффициенты на победу
    expected = home_strength / max(away_strength, 0.01)
    win_prob = expected / (1 + expected)
    win_prob = max(0.1, min(0.9, win_prob))
    
    home_odds = round(1 / win_prob, 2)
    away_odds = round(1 / (1 - win_prob), 2)
    
    # Фора по мячам (всегда на основе очков, если они есть)
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = home_pts_strength / max(away_pts_strength, 0.01)
        
        expected_diff = (pts_ratio - 1) * 22  # корректировка
        expected_diff = max(-18, min(18, expected_diff))
        handicap_value = round(expected_diff / 0.5) * 0.5
        
        is_home_favorite = handicap_value < 0
        abs_handicap = abs(handicap_value)
        
        if abs_handicap < 0.5:
            handicap_line = "Ожидается равный матч"
        elif is_home_favorite:
            handicap_line = f"{home['name']} (фаворит) дома с форой {abs_handicap}"
        else:
            handicap_line = f"{away['name']} (фаворит) в гостях с форой -{abs_handicap}"
    else:
        handicap_line = "Нет данных по очкам для расчета форы"
    
    return jsonify({
        'success': True,
        'prediction': {
            'home_team': home['name'],
            'away_team': away['name'],
            'home_sets': f"{home['sets_won']}:{home['sets_lost']}",
            'away_sets': f"{away['sets_won']}:{away['sets_lost']}",
            'home_points': f"{home['points_won']}:{home['points_lost']}" if home['points_won'] else None,
            'away_points': f"{away['points_won']}:{away['points_lost']}" if away['points_won'] else None,
            'home_win_odds': home_odds,
            'away_win_odds': away_odds,
            'handicap_line': handicap_line
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
