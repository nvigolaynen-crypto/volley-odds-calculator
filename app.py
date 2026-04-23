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
    
    # Ищем все таблицы
    tables = soup.find_all('table')
    
    best_table = None
    max_data_rows = 0
    
    for table in tables:
        rows = table.find_all('tr')
        data_rows = sum(1 for row in rows if row.find_all('td'))
        if data_rows > max_data_rows and data_rows >= 2:
            max_data_rows = data_rows
            best_table = table
    
    if not best_table:
        return []
    
    teams = []
    rows = best_table.find_all('tr')
    
    # Пропускаем заголовок если есть
    start_row = 0
    if rows and rows[0].find_all('th'):
        start_row = 1
    
    for row in rows[start_row:]:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        
        # Ищем название команды
        team_name = None
        for col in cols[:4]:
            text = col.get_text().strip()
            text = re.sub(r'[\n\r\t]+', ' ', text).strip()
            if text and not re.match(r'^\d+$', text) and 2 <= len(text) <= 50:
                team_name = text
                break
        
        if not team_name:
            continue
        
        # Собираем все числа из строки
        numbers = []
        for col in cols:
            text = col.get_text().strip()
            
            # Формат "3:1" или "3-1"
            ratio_match = re.search(r'(\d+)[:-](\d+)', text)
            if ratio_match:
                numbers.append(int(ratio_match.group(1)))
                numbers.append(int(ratio_match.group(2)))
            else:
                num_match = re.search(r'\b(\d+)\b', text)
                if num_match:
                    num = int(num_match.group(1))
                    if num < 500:
                        numbers.append(num)
        
        # Убираем дубликаты сохраняя порядок
        seen = set()
        numbers = [x for x in numbers if not (x in seen or seen.add(x))]
        
        # Извлекаем сеты (обычно первые два числа)
        sets_won = numbers[0] if len(numbers) > 0 else 0
        sets_lost = numbers[1] if len(numbers) > 1 else 0
        
        # Извлекаем очки (если есть)
        points_won = None
        points_lost = None
        
        if len(numbers) >= 4:
            points_won = numbers[2]
            points_lost = numbers[3]
        
        # Проверяем колонки на наличие очков в формате "25:20"
        if not points_won:
            for col in cols:
                text = col.get_text().strip()
                if ':' in text:
                    parts = text.split(':')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        if int(parts[0]) > 30 or int(parts[1]) > 30:  # Похоже на очки
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
            return jsonify({'error': 'Не удалось найти данные в таблице'}), 404
        
        return jsonify({
            'success': True,
            'teams': teams,
            'count': len(teams),
            'url': url
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Превышено время ожидания'}), 408
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Не удалось подключиться к сайту'}), 500
    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    """Расчет коэффициентов и форы по мячам"""
    data = request.json
    teams = data.get('teams', [])
    home_name = data.get('home_team')
    away_name = data.get('away_team')
    neutral = data.get('neutral_ground', False)
    
    home = next((t for t in teams if t['name'] == home_name), None)
    away = next((t for t in teams if t['name'] == away_name), None)
    
    if not home or not away:
        return jsonify({'error': 'Команды не найдены'}), 400
    
    # Коэффициент на победу домашней команды
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    home_advantage = 1.05 if not neutral else 1.0
    
    expected_ratio = (home_strength * home_advantage) / max(away_strength, 0.01)
    win_prob = expected_ratio / (1 + expected_ratio)
    win_prob = max(0.08, min(0.92, win_prob))
    
    home_win_odds = round(1 / win_prob, 2)
    away_win_odds = round(1 / (1 - win_prob), 2)
    
    # ФОРА ПО МЯЧАМ (ОЧКАМ)
    handicap_value = 0
    handicap_odds = 1.85
    home_handicap = 0
    away_handicap = 0
    
    if home['points_won'] and away['points_won']:
        # РАСЧЕТ ФОРЫ НА ОСНОВЕ ОЧКОВ
        home_pts_avg = home['points_won'] / max(home['sets_won'] + home['sets_lost'], 1) * 3
        away_pts_avg = away['points_won'] / max(away['sets_won'] + away['sets_lost'], 1) * 3
        
        home_pts_strength = home['points_won'] / max(home['points_lost'], 1)
        away_pts_strength = away['points_won'] / max(away['points_lost'], 1)
        
        pts_ratio = (home_pts_strength * home_advantage) / max(away_pts_strength, 0.01)
        
        # Ожидаемая разница в очках за матч
        # В волейболе средний сет ~46 очков, матч ~138 очков
        expected_points_diff = (pts_ratio - 1) * 70
        
        # Ограничиваем разумными пределами
        expected_points_diff = max(-25, min(25, expected_points_diff))
        
        # Фора для домашней команды (отрицательная - фаворит)
        if expected_points_diff > 3:
            handicap_value = -round(expected_points_diff / 3) * 1.5
            home_handicap = handicap_value
            away_handicap = -handicap_value
        elif expected_points_diff < -3:
            handicap_value = round(abs(expected_points_diff) / 3) * 1.5
            home_handicap = handicap_value
            away_handicap = -handicap_value
        else:
            handicap_value = 0
        
        # Округляем до .5
        handicap_value = round(handicap_value * 2) / 2
        
        # Коэффициент на фору зависит от величины
        if abs(handicap_value) >= 8:
            handicap_odds = 2.20
        elif abs(handicap_value) >= 6:
            handicap_odds = 2.00
        elif abs(handicap_value) >= 4:
            handicap_odds = 1.90
        elif abs(handicap_value) >= 2:
            handicap_odds = 1.85
        else:
            handicap_odds = 1.80
        
        handicap_odds = round(handicap_odds, 2)
    
    else:
        # Если нет данных по очкам - рассчитываем фору на основе сетов
        set_ratio = home_strength / max(away_strength, 0.01)
        expected_sets_diff = (set_ratio - 1) * 2
        
        if expected_sets_diff > 0.5:
            handicap_value = -round(expected_sets_diff * 2)
            home_handicap = handicap_value
        elif expected_sets_diff < -0.5:
            handicap_value = round(abs(expected_sets_diff) * 2)
            home_handicap = handicap_value
        else:
            handicap_value = 0
        
        handicap_value = max(-10, min(10, handicap_value))
        handicap_odds = 1.85
    
    # Формулировка форы
    if handicap_value < 0:
        handicap_line = f"Фора {home['name']} ({handicap_value})"
        handicap_text = f"Прогноз: {home['name']} выиграет с разницей минимум {abs(handicap_value)} очков"
    elif handicap_value > 0:
        handicap_line = f"Фора {away['name']} (+{handicap_value})"
        handicap_text = f"Прогноз: {away['name']} не проиграет с разницей более {handicap_value} очков"
    else:
        handicap_line = "Тотал ровно"
        handicap_text = "Прогноз: ожидается равный матч"
    
    return jsonify({
        'success': True,
        'prediction': {
            'home_team': home['name'],
            'away_team': away['name'],
            'home_win_odds': home_win_odds,
            'away_win_odds': away_win_odds,
            'handicap_line': handicap_line,
            'handicap_odds': handicap_odds,
            'handicap_text': handicap_text,
            'home_sets': f"{home['sets_won']}:{home['sets_lost']}",
            'away_sets': f"{away['sets_won']}:{away['sets_lost']}",
            'home_points': f"{home['points_won']}:{home['points_lost']}" if home['points_won'] else None,
            'away_points': f"{away['points_won']}:{away['points_lost']}" if away['points_won'] else None
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
