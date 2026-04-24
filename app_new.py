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
    return send_from_directory('static', 'index_new.html')

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
    
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    expected = home_strength / max(away_strength, 0.01)
    win_prob = expected / (1 + expected)
    win_prob = max(0.1, min(0.9, win_prob))
    
    home_odds = round(1 / win_prob, 2)
    away_odds = round(1 / (1 - win_prob), 2)
    
    if home['points_won'] and away['points_won']:
        home_pts = home['points_won'] / max(home['points_lost'], 1)
        away_pts = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = home_pts / max(away_pts, 0.01)
        
        expected_diff = (pts_ratio - 1) * 15
        expected_diff = max(-12, min(12, expected_diff))
        
        if expected_diff < -2:
            handicap = round(expected_diff)
            line = f"Фора {home['name']} ({handicap})"
            odds = round(1.85 + abs(handicap) * 0.05, 2)
            text = f"Прогноз: {home['name']} выиграет с разницей {abs(handicap)}+ очков"
        elif expected_diff > 2:
            handicap = round(expected_diff)
            line = f"Фора {away['name']} (+{handicap})"
            odds = round(1.85 + handicap * 0.05, 2)
            text = f"Прогноз: {away['name']} не проиграет с разницей более {handicap} очков"
        else:
            line = "Тотал ровно"
            odds = 1.85
            text = "Прогноз: ожидается равный матч"
    else:
        line = "Нет данных по очкам (нужны для расчета форы)"
        odds = 1.85
        text = "В таблице нет данных по набранным очкам"
    
    return jsonify({
        'success': True,
        'prediction': {
            'home_team': home['name'],
            'away_team': away['name'],
            'home_sets': f"{home['sets_won']}:{home['sets_lost']}",
            'away_sets': f"{away['sets_won']}:{away['sets_lost']}",
            'home_win_odds': home_odds,
            'away_win_odds': away_odds,
            'handicap_line': line,
            'handicap_odds': odds,
            'handicap_text': text
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)