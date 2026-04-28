from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

def parse_dataproject_table(soup):
    # Найти таблицу
    table = soup.find('table', class_=re.compile(r'grid'))
    if not table:
        table = soup.find('table', id=re.compile(r'grd', re.I))
    if not table:
        return None

    rows = table.find_all('tr')
    if len(rows) < 2:
        return None

    # Попытаемся определить заголовки
    header_row = None
    for row in rows:
        ths = row.find_all('th')
        if ths:
            header_row = ths
            break

    # Определим индексы по тексту заголовков
    set_won_idx = set_lost_idx = points_won_idx = points_lost_idx = None
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

    # Если заголовки не помогли, проанализируем первые несколько строк данных
    # чтобы определить, где сеты (маленькие числа) и где очки (большие)
    sample_row = None
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) >= 5:
            sample_row = cols
            break

    if sample_row and (set_won_idx is None or set_lost_idx is None):
        # Соберём все числа из первой строки и определим диапазоны
        numbers = []
        for i, col in enumerate(sample_row):
            text = col.get_text().strip()
            nums = re.findall(r'\b(\d+)\b', text)
            for n in nums:
                val = int(n)
                if val < 5000:
                    numbers.append((i, val))
        # Сортируем по значению
        numbers.sort(key=lambda x: x[1])
        # Самые маленькие (первые два) – вероятно сеты, самые большие (последние два) – очки
        if len(numbers) >= 2:
            # Проверим, что они действительно маленькие (0-150)
            small_indices = [idx for idx, val in numbers if val <= 150]
            if len(small_indices) >= 2:
                set_won_idx, set_lost_idx = small_indices[0], small_indices[1]
        if len(numbers) >= 4:
            large_indices = [idx for idx, val in numbers if val >= 500]
            if len(large_indices) >= 2:
                points_won_idx, points_lost_idx = large_indices[0], large_indices[1]

    teams = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) < 5:
            continue

        # Название команды – обычно первая или вторая колонка с текстом
        team_name = None
        for i in range(min(3, len(cols))):
            text = cols[i].get_text().strip()
            if text and not text.isdigit() and len(text) > 1:
                team_name = text
                break
        if not team_name:
            continue

        # Функция безопасного извлечения числа из колонки
        def get_int(col):
            try:
                return int(col.get_text().strip())
            except:
                return 0

        sets_won = get_int(cols[set_won_idx]) if set_won_idx is not None and set_won_idx < len(cols) else 0
        sets_lost = get_int(cols[set_lost_idx]) if set_lost_idx is not None and set_lost_idx < len(cols) else 0
        points_won = get_int(cols[points_won_idx]) if points_won_idx is not None and points_won_idx < len(cols) else None
        points_lost = get_int(cols[points_lost_idx]) if points_lost_idx is not None and points_lost_idx < len(cols) else None

        # Если сеты не найдены, попробуем угадать по наличию двоеточия в ячейках
        if sets_won == 0 and sets_lost == 0:
            for col in cols:
                text = col.get_text().strip()
                if ':' in text:
                    parts = text.split(':')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        s1, s2 = int(parts[0]), int(parts[1])
                        if s1 <= 150 and s2 <= 150:
                            sets_won, sets_lost = s1, s2
                            break

        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won if points_won and points_won > 0 else None,
            'points_lost': points_lost if points_lost and points_lost > 0 else None
        })

    return teams

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
    
    expected = home_strength / max(away_strength, 0.01)
    win_prob = expected / (1 + expected)
    win_prob = max(0.1, min(0.9, win_prob))
    
    home_odds = round(1 / win_prob, 2)
    away_odds = round(1 / (1 - win_prob), 2)
    
    if home['points_won'] and away['points_won'] and home['points_won'] > 0 and away['points_won'] > 0:
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = home_pts_strength / max(away_pts_strength, 0.01)
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
            'home_win_odds': home_odds,
            'away_win_odds': away_odds,
            'handicap_line': handicap_line
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
