from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

def parse_html_table(html_content, url):
    """Универсальный парсер HTML таблиц"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Ищем все таблицы на странице
    tables = soup.find_all('table')
    
    # Пробуем найти таблицу с данными (не заголовками)
    best_table = None
    max_data_rows = 0
    
    for table in tables:
        rows = table.find_all('tr')
        # Считаем строки с td (данные)
        data_rows = sum(1 for row in rows if row.find_all('td'))
        if data_rows > max_data_rows and data_rows >= 2:
            max_data_rows = data_rows
            best_table = table
    
    if not best_table:
        return []
    
    teams = []
    rows = best_table.find_all('tr')
    
    # Пропускаем первую строку если это заголовок
    start_row = 0
    first_row = rows[0].find_all('th') if rows else []
    if first_row:
        start_row = 1
    
    for row in rows[start_row:]:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        
        # Ищем название команды (первая нецифровая колонка)
        team_name = None
        for col in cols[:4]:
            text = col.get_text().strip()
            # Очищаем от лишних символов
            text = re.sub(r'[\n\r\t]+', ' ', text)
            text = text.strip()
            # Название команды: не число, не пустое, не слишком длинное
            if text and not re.match(r'^\d+$', text) and len(text) < 50 and len(text) > 1:
                team_name = text
                break
        
        if not team_name:
            continue
        
        # Ищем все числа в строке (сеты, очки, победы)
        numbers = []
        for col in cols:
            text = col.get_text().strip()
            # Ищем числа (в том числе в формате "3-1" или "3:1")
            # Сначала проверяем формат сетов
            ratio_match = re.search(r'(\d+)[:-](\d+)', text)
            if ratio_match:
                numbers.append(int(ratio_match.group(1)))
                numbers.append(int(ratio_match.group(2)))
            else:
                num_match = re.search(r'\b(\d+)\b', text)
                if num_match:
                    num = int(num_match.group(1))
                    if num < 500:  # Разумное ограничение
                        numbers.append(num)
        
        # Убираем дубликаты
        numbers = list(dict.fromkeys(numbers))
        
        # Извлекаем сеты (обычно первая или вторая пара чисел)
        sets_won = 0
        sets_lost = 0
        
        if len(numbers) >= 2:
            sets_won = numbers[0]
            sets_lost = numbers[1]
        elif len(numbers) >= 1:
            sets_won = numbers[0]
        
        # Ищем очки (если есть)
        points_won = None
        points_lost = None
        
        if len(numbers) >= 4:
            points_won = numbers[2]
            points_lost = numbers[3]
        elif ':' in str(cols):
            for col in cols:
                text = col.get_text().strip()
                if ':' in text and len(text.split(':')) == 2:
                    parts = text.split(':')
                    if parts[0].isdigit() and parts[1].isdigit():
                        points_won = int(parts[0])
                        points_lost = int(parts[1])
                        break
        
        teams.append({
            'name': team_name,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'points_won': points_won,
            'points_lost': points_lost
        })
    
    return teams

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/parse', methods=['POST'])
def parse_standings():
    """Парсинг турнирной таблицы по URL"""
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL не указан'}), 400
    
    try:
        # Заголовки чтобы выглядеть как браузер
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        teams = parse_html_table(response.text, url)
        
        if not teams:
            return jsonify({'error': 'Не удалось найти данные в таблице. Проверьте URL.'}), 404
        
        return jsonify({
            'success': True,
            'teams': teams,
            'count': len(teams),
            'url': url
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Превышено время ожидания. Сайт слишком долго отвечает.'}), 408
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Не удалось подключиться к сайту. Проверьте URL.'}), 500
    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """Расчет коэффициентов"""
    data = request.json
    teams = data.get('teams', [])
    home_name = data.get('home_team')
    away_name = data.get('away_team')
    neutral = data.get('neutral_ground', False)
    
    home = next((t for t in teams if t['name'] == home_name), None)
    away = next((t for t in teams if t['name'] == away_name), None)
    
    if not home or not away:
        return jsonify({'error': 'Команды не найдены'}), 400
    
    # Коэффициенты на победу по сетам
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    home_advantage = 1.05 if not neutral else 1.0
    
    expected_ratio = (home_strength * home_advantage) / max(away_strength, 0.01)
    win_prob = expected_ratio / (1 + expected_ratio)
    win_prob = max(0.05, min(0.95, win_prob))
    
    home_win_odds = round(1 / win_prob, 2)
    away_win_odds = round(1 / (1 - win_prob), 2)
    
    # Фора по очкам
    handicap_line = "Тотал ровно"
    handicap_odds = 1.85
    
    if home.get('points_won') and away.get('points_won'):
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        pts_ratio = (home_pts_strength * home_advantage) / max(away_pts_strength, 0.01)
        
        avg_pts = 46
        expected_margin = (pts_ratio - 1) * avg_pts * 2
        expected_margin = max(-12, min(12, expected_margin))
        
        handicap = round(expected_margin / 1.5)
        
        if handicap < -1:
            handicap_line = f"Фора {home['name']} ({handicap})"
            handicap_odds = round(1.85 + abs(handicap) * 0.05, 2)
        elif handicap > 1:
            handicap_line = f"Фора {away['name']} (+{handicap})"
            handicap_odds = round(1.85 + abs(handicap) * 0.05, 2)
    
    return jsonify({
        'success': True,
        'prediction': {
            'home_team': home['name'],
            'away_team': away['name'],
            'home_win_odds': home_win_odds,
            'away_win_odds': away_win_odds,
            'handicap_line': handicap_line,
            'handicap_odds': handicap_odds,
            'home_sets': f"{home['sets_won']}:{home['sets_lost']}",
            'away_sets': f"{away['sets_won']}:{away['sets_lost']}"
        }
    })

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
