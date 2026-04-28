from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import os
from collections import defaultdict

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

def parse_fpv_standings(html, merge_phases=False):
    """Парсер для fpv-web.dataproject.com
       merge_phases=False – только первый этап (1ª Fase)
       merge_phases=True – объединить все этапы, суммируя статистику команд
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    if not merge_phases:
        # Берём только первую вкладку (1ª Fase) – её ID = Content_Main_446
        first_tab = soup.find('div', id='Content_Main_446')
        if not first_tab:
            # fallback: ищем любую вкладку с классом rmpView
            first_tab = soup.find('div', class_='rmpView')
        if not first_tab:
            return []
        container = first_tab
    else:
        # Будем искать все строки во всех вкладках
        container = soup  # искать по всему документу
    
    # Находим строки таблицы
    if merge_phases:
        rows = soup.find_all('tr', class_=lambda c: c and ('RG_Standing_Main_AltBackColor' in c))
    else:
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
    
    # Преобразуем в список
    teams = []
    for name, stats in teams_dict.items():
        teams.append({
            'name': name,
            'sets_won': stats['sets_won'],
            'sets_lost': stats['sets_lost'],
            'points_won': stats['points_won'] if stats['points_won'] > 0 else None,
            'points_lost': stats['points_lost'] if stats['points_lost'] > 0 else None
        })
    
    # Сортируем по сетевым показателям (по желанию)
    teams.sort(key=lambda x: x['sets_won'] / max(x['sets_lost'], 1), reverse=True)
    return teams

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/parse', methods=['POST'])
def parse():
    data = request.json
    url = data.get('url')
    merge_phases = data.get('merge_phases', False)  # новый параметр
    
    if not url:
        return jsonify({'error': 'URL не указан'}), 400
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        teams = parse_fpv_standings(response.text, merge_phases=merge_phases)
        
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
    expected = home_strength / max(away_strength, 0.01)
    win_prob = expected / (1 + expected)
    win_prob = max(0.1, min(0.9, win_prob))
    
    home_win_odds = round(1 / win_prob, 2)
    away_win_odds = round(1 / (1 - win_prob), 2)
    
    # Фора по мячам
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = home_pts_strength / max(away_pts_strength, 0.01)
        expected_diff = (pts_ratio - 1) * 22
        expected_diff = max(-18, min(18, expected_diff))
        handicap = round(expected_diff / 0.5) * 0.5
        
        if abs(handicap) < 0.5:
            handicap_line = "Ожидается равный матч"
        elif handicap < 0:
            handicap_line = f"{home['name']} (фаворит) дома с форой {abs(handicap)}"
        else:
            handicap_line = f"{away['name']} (фаворит) в гостях с форой -{handicap}"
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
