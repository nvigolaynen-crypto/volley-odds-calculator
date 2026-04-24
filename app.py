from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

def parse_teams(html):
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    
    for table in tables:
        teams = []
        rows = table.find_all('tr')
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            
            team_name = None
            for col in cols[:3]:
                text = col.get_text().strip()
                if text and not text.isdigit() and len(text) > 1:
                    team_name = text
                    break
            
            if not team_name:
                continue
            
            numbers = []
            for col in cols:
                text = col.get_text().strip()
                nums = re.findall(r'\d+', text)
                for num in nums:
                    n = int(num)
                    if n < 500:
                        numbers.append(n)
            
            numbers = list(dict.fromkeys(numbers))
            
            sets_won = numbers[0] if len(numbers) > 0 else 0
            sets_lost = numbers[1] if len(numbers) > 1 else 0
            points_won = numbers[2] if len(numbers) > 2 else None
            points_lost = numbers[3] if len(numbers) > 3 else None
            
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
        
        teams = parse_teams(response.text)
        
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
    
    # Расчет силы команд по сетам
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    
    # Коэффициенты на победу
    expected = home_strength / max(away_strength, 0.01)
    win_prob = expected / (1 + expected)
    win_prob = max(0.1, min(0.9, win_prob))
    
    home_odds = round(1 / win_prob, 2)
    away_odds = round(1 / (1 - win_prob), 2)
    
    # РАСЧЕТ ФОРЫ ПО МЯЧАМ (среднее значение, без коэффициента)
    handicap_value = 0
    is_home_favorite = True
    
    if home['points_won'] and away['points_won']:
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = home_pts_strength / max(away_pts_strength, 0.01)
        
        # Расчет ожидаемой разницы в очках
        expected_diff = (pts_ratio - 1) * 25
        expected_diff = max(-25, min(25, expected_diff))
        
        # Округляем до 0.5
        handicap_value = round(expected_diff / 0.5) * 0.5
        handicap_value = max(-25, min(25, handicap_value))
        
        is_home_favorite = handicap_value < 0
        
    else:
        # Если нет данных по очкам - на основе сетов
        set_ratio = home_strength / max(away_strength, 0.01)
        expected_diff = (set_ratio - 1) * 8
        expected_diff = max(-15, min(15, expected_diff))
        handicap_value = round(expected_diff / 0.5) * 0.5
        is_home_favorite = handicap_value < 0
    
    # Формулировка форы (без коэффициента)
    abs_handicap = abs(handicap_value)
    
    if abs_handicap < 0.5:
        handicap_line = "Ожидается равный матч"
    elif is_home_favorite:
        handicap_line = f"{home['name']} (фаворит) дома с форой {abs_handicap}"
    else:
        handicap_line = f"{away['name']} (фаворит) в гостях с форой -{abs_handicap}"
    
    return jsonify({
        'success': True,
        'prediction': {
            'home_team': home['name'],
            'away_team': away['name'],
            'home_sets': f"{home['sets_won']}:{home['sets_lost']}",
            'away_sets': f"{away['sets_won']}:{away['sets_lost']}",
            'home_win_odds': home_odds,
            'away_win_odds': away_odds,
            'handicap_line': handicap_line
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
