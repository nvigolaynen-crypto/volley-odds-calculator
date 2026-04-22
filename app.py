from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from parsers import SimpleParser
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)
parser = SimpleParser()

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
        teams = parser.parse(url)
        return jsonify({
            'success': True,
            'teams': teams,
            'count': len(teams)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    teams = data.get('teams', [])
    home_name = data.get('home_team')
    away_name = data.get('away_team')
    neutral = data.get('neutral_ground', False)
    
    home = next((t for t in teams if t['name'] == home_name), None)
    away = next((t for t in teams if t['name'] == away_name), None)
    
    if not home or not away:
        return jsonify({'error': 'Команды не найдены'}), 400
    
    # Расчет вероятности по сетам
    home_strength = home['sets_won'] / max(home['sets_lost'], 1)
    away_strength = away['sets_won'] / max(away['sets_lost'], 1)
    home_advantage = 1.05 if not neutral else 1.0
    
    expected = (home_strength * home_advantage) / max(away_strength, 0.01)
    probability = expected / (1 + expected)
    probability = max(0.05, min(0.95, probability))
    
    if probability > 0.5:
        recommendation = f"Ставка на {home['name']}"
        fair_odds = round(1 / probability, 2)
    else:
        recommendation = f"Ставка на {away['name']}"
        fair_odds = round(1 / (1 - probability), 2)
    
    return jsonify({
        'success': True,
        'prediction': {
            'home_team': home['name'],
            'away_team': away['name'],
            'probability': round(probability, 4),
            'odds': round(1 / probability, 2),
            'recommendation': recommendation,
            'fair_odds': fair_odds,
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