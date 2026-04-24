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
            if len(cols) < 5:
                continue
            
            # Название команды (обычно 1-2 колонка)
            team_name = None
            for col in cols[:3]:
                text = col.get_text().strip()
                if text and not text.isdigit() and len(text) > 1:
                    team_name = text
                    break
            
            if not team_name:
                continue
            
            # Собираем все числа из строки
            all_numbers = []
            for idx, col in enumerate(cols):
                text = col.get_text().strip()
                # Ищем числа в ячейке
                nums = re.findall(r'\b(\d+)\b', text)
                for num in nums:
                    n = int(num)
                    # Исключаем слишком большие (не сеты)
                    if n < 5000:
                        all_numbers.append({'index': idx, 'value': n, 'text': text})
            
            # АНАЛИЗ ДАННЫХ:
            # В волейбольной таблице колонки обычно идут в порядке:
            # 1. Название команды
            # 2. Игры (матчи)
            # 3. Победы
            # 4. Поражения  
            # 5. Сеты выиграно
            # 6. Сеты проиграно
            # 7. Очки выиграно (мячи)
            # 8. Очки проиграно (мячи)
            
            sets_won = 0
            sets_lost = 0
            points_won = None
            points_lost = None
            
            # Ищем числа в диапазоне сетов (0-150) - это обычно сеты
            set_candidates = [n for n in all_numbers if n['value'] <= 150 and n['value'] > 0]
            
            # Ищем большие числа (1000+) - это очки/мячи
            points_candidates = [n for n in all_numbers if n['value'] >= 500 and n['value'] < 3000]
            
            # Если нашли сеты - берем первые два
            if len(set_candidates) >= 2:
                sets_won = set_candidates[0]['value']
                sets_lost = set_candidates[1]['value']
            elif len(set_candidates) == 1:
                sets_won = set_candidates[0]['value']
            
            # Если нашли очки - берем
            if len(points_candidates) >= 2:
                points_won = points_candidates[0]['value']
                points_lost = points_candidates[1]['value']
            
            # Дополнительная проверка: ищем колонки с двоеточием
            for col in cols:
                text = col.get_text().strip()
                if ':' in text:
                    parts = text.split(':')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        p1 = int(parts[0])
                        p2 = int(parts[1])
                        # Если оба числа маленькие (0-150) - это сеты
                        if p1 <= 150 and p2 <= 150:
                            sets_won = p1
                            sets_lost = p2
                        # Если оба числа большие (500+) - это очки
                        elif p1 >= 500 and p2 >= 500:
                            points_won = p1
                            points_lost = p2
            
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
    home_strength = home['sets_won'] / max(home['sets_lost'], 1) if home['sets_lost'] > 0 else home['sets_won']
    away_strength = away['sets_won'] / max(away['sets_lost'], 1) if away['sets_lost'] > 0 else away['sets_won']
    
    # Коэффициенты на победу
    expected = home_strength / max(away_strength, 0.01)
    win_prob = expected / (1 + expected)
    win_prob = max(0.1, min(0.9, win_prob))
    
    home_odds = round(1 / win_prob, 2)
    away_odds = round(1 / (1 - win_prob), 2)
    
    # РАСЧЕТ ФОРЫ ПО МЯЧАМ
    handicap_value = 0
    is_home_favorite = True
    
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = home_pts_strength / max(away_pts_strength, 0.01)
        
        # Расчет ожидаемой разницы в очках за матч
        expected_diff = (pts_ratio - 1) * 25
        expected_diff = max(-20, min(20, expected_diff))
        
        handicap_value = round(expected_diff / 0.5) * 0.5
        is_home_favorite = handicap_value < 0
        
    elif home['sets_won'] > 0 and away['sets_won'] > 0:
        # Если нет очков - на основе сетов
        set_ratio = home_strength / max(away_strength, 0.01)
        expected_diff = (set_ratio - 1) * 10
        expected_diff = max(-15, min(15, expected_diff))
        handicap_value = round(expected_diff / 0.5) * 0.5
        is_home_favorite = handicap_value < 0
    
    abs_handicap = abs(handicap_value)
    
    if abs_handicap < 0.5 or handicap_value == 0:
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
