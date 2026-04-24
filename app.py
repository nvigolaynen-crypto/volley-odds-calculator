from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

def parse_dataproject_table(soup):
    """Парсер для DataProject с автоопределением колонок"""
    # Ищем таблицу с классом grid или grid_lines
    table = soup.find('table', class_=re.compile(r'grid'))
    if not table:
        # Попробуем найти таблицу по id
        table = soup.find('table', id=re.compile(r'grd', re.I))
    if not table:
        return None
    
    # Получаем все строки
    rows = table.find_all('tr')
    if len(rows) < 2:
        return None
    
    # Пробуем найти строку заголовков, чтобы определить индексы
    header_row = None
    for row in rows:
        ths = row.find_all('th')
        if ths:
            header_row = ths
            break
    
    # Если есть заголовки, ищем по тексту
    set_won_idx = None
    set_lost_idx = None
    points_won_idx = None
    points_lost_idx = None
    
    if header_row:
        for i, th in enumerate(header_row):
            text = th.get_text().lower()
            if 'set' in text and ('w' in text or 'vinti' in text or 'ganados' in text or 'выигр' in text):
                set_won_idx = i
            elif 'set' in text and ('l' in text or 'persi' in text or 'perdidos' in text or 'проигр' in text):
                set_lost_idx = i
            elif 'point' in text or 'punti' in text or 'очк' in text or 'ball' in text:
                if 'for' in text or 'fatti' in text or 'забит' in text:
                    points_won_idx = i
                elif 'against' in text or 'subiti' in text or 'пропущ' in text:
                    points_lost_idx = i
    
    # Если не нашли по заголовкам, будем определять по значениям
    teams = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) < 5:
            continue
        
        # Название команды – обычно первая или вторая колонка
        team_name = None
        for i in range(min(3, len(cols))):
            text = cols[i].get_text().strip()
            if text and not text.isdigit() and len(text) > 1:
                team_name = text
                break
        if not team_name:
            continue
        
        # Собираем все числа из ячейки (учитываем, что в ячейке может быть несколько чисел)
        numbers = []
        for col in cols:
            text = col.get_text().strip()
            # Ищем числа в тексте
            nums = re.findall(r'\b(\d+)\b', text)
            for n in nums:
                val = int(n)
                # Пропускаем слишком большие (больше 5000) - это могут быть ID
                if val < 5000:
                    numbers.append(val)
        
        # Если есть индексы из заголовков – используем их
        if set_won_idx is not None and set_won_idx < len(cols):
            set_won = int(cols[set_won_idx].get_text().strip()) if cols[set_won_idx].get_text().strip().isdigit() else 0
        else:
            set_won = 0
        if set_lost_idx is not None and set_lost_idx < len(cols):
            set_lost = int(cols[set_lost_idx].get_text().strip()) if cols[set_lost_idx].get_text().strip().isdigit() else 0
        else:
            set_lost = 0
        
        if points_won_idx is not None and points_won_idx < len(cols):
            points_won = int(cols[points_won_idx].get_text().strip()) if cols[points_won_idx].get_text().strip().isdigit() else None
        else:
            points_won = None
        if points_lost_idx is not None and points_lost_idx < len(cols):
            points_lost = int(cols[points_lost_idx].get_text().strip()) if cols[points_lost_idx].get_text().strip().isdigit() else None
        else:
            points_lost = None
        
        # Если индексы не определились – пытаемся угадать по значениям
        if set_won == 0 and set_lost == 0 and len(numbers) >= 2:
            # Сортируем числа
            numbers_sorted = sorted(numbers)
            # Самые большие числа – это очки (обычно > 500)
            large = [n for n in numbers_sorted if n > 500]
            # Остальные – сеты
            small = [n for n in numbers_sorted if n <= 150]
            
            if len(small) >= 2:
                set_won = small[-2] if len(small) >= 2 else 0
                set_lost = small[-1] if len(small) >= 2 else 0
            elif len(small) == 1:
                set_won = small[0]
            
            if len(large) >= 2:
                points_won = large[-2]
                points_lost = large[-1]
        
        # Если у нас есть и сеты и очки – добавляем
        if team_name:
            teams.append({
                'name': team_name,
                'sets_won': set_won,
                'sets_lost': set_lost,
                'points_won': points_won,
                'points_lost': points_lost
            })
    
    return teams if teams else None

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
        
        teams = parse_dataproject_table(soup)
        
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
    
    # Используем очки, если есть
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
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
    
    # Фора по мячам (только на основе очков)
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = home_pts_strength / max(away_pts_strength, 0.01)
        
        # Коэффициент перевода в разницу очков
        expected_diff = (pts_ratio - 1) * 22
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
