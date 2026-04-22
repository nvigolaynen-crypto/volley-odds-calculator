import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

class SimpleParser:
    """Простой парсер для турнирных таблиц"""
    
    def parse(self, url: str) -> List[Dict]:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем таблицу
        table = soup.find('table')
        if not table:
            return []
        
        teams = []
        rows = table.find_all('tr')[1:]  # Пропускаем заголовок
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            
            # Ищем название команды (первая нецифровая колонка)
            team_name = None
            for col in cols[:3]:
                text = col.get_text().strip()
                if text and not text.isdigit() and len(text) > 1:
                    team_name = text
                    break
            
            if not team_name:
                continue
            
            # Ищем числа (сеты)
            numbers = []
            for col in cols:
                text = col.get_text().strip()
                if text.isdigit():
                    numbers.append(int(text))
            
            sets_won = numbers[0] if len(numbers) > 0 else 0
            sets_lost = numbers[1] if len(numbers) > 1 else 0
            
            teams.append({
                'name': team_name,
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': None,
                'points_lost': None
            })
        
        return teams