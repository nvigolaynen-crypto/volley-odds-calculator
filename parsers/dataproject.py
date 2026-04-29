import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers)
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Находим таблицу с итоговой статистикой (класс RG_Standing_Main или просто таблица с нужными id)
        # В HTML данные находятся в тегах с id="SetsWon", "SetsLost", "PuntiFatti", "PuntiSubiti"
        # Ищем все строки, содержащие эти элементы
        team_rows = []
        # Ищем все строки, содержащие span или p с id="TeamName"
        for team_span in soup.find_all('span', id='TeamName'):
            row = team_span.find_parent('tr')
            if row:
                team_rows.append(row)

        if not team_rows:
            # Альтернативный поиск: ищем все строки в tbody таблицы RG_Standing_Main
            main_table = soup.find('table', class_='RG_Standing_Main')
            if not main_table:
                # Попробуем найти таблицу по другому классу
                main_table = soup.find('table', class_='rgMasterTable')
            if main_table:
                tbody = main_table.find('tbody')
                if tbody:
                    team_rows = tbody.find_all('tr')

        stats = {}
        for row in team_rows:
            # Название команды
            team_name_tag = row.find('span', id='TeamName')
            if not team_name_tag:
                # возможно, название в ссылке
                link = row.find('a', href=re.compile(r'CompetitionTeamDetails.aspx'))
                if link:
                    team_name = link.get_text(strip=True)
                else:
                    continue
            else:
                team_name = team_name_tag.get_text(strip=True)

            # Извлекаем сеты
            sets_won_tag = row.find('span', id='SetsWon')
            sets_lost_tag = row.find('span', id='SetsLost')
            if sets_won_tag and sets_lost_tag:
                sets_won = int(sets_won_tag.get_text(strip=True))
                sets_lost = int(sets_lost_tag.get_text(strip=True))
            else:
                # возможно, данные в других тегах или колонках
                continue

            # Извлекаем очки
            points_won_tag = row.find('span', id='PuntiFatti')
            points_lost_tag = row.find('span', id='PuntiSubiti')
            if points_won_tag and points_lost_tag:
                points_won = int(points_won_tag.get_text(strip=True))
                points_lost = int(points_lost_tag.get_text(strip=True))
            else:
                points_won = points_lost = 0

            stats[team_name] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }

        if not stats:
            raise ValueError("Не удалось извлечь статистику для команд")

        df = pd.DataFrame.from_dict(stats, orient='index')
        df = df.reset_index().rename(columns={'index': 'Команда'})
        df['Сеты'] = df['sets_won'].astype(str) + ':' + df['sets_lost'].astype(str)
        df['Мячи'] = df['points_won'].astype(str) + ':' + df['points_lost'].astype(str)
        df = df.sort_values('sets_won', ascending=False)
        return df[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()
