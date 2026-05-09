import subprocess
import os
import re
import pandas as pd
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        fed_match = re.search(r'https?://([a-z]+)-web\.dataproject\.com', url)
        if not fed_match:
            raise ValueError("Не удалось определить fed")
        fed = fed_match.group(1)
        comp_match = re.search(r'[?&]ID=(\d+)', url)
        if not comp_match:
            raise ValueError("Не удалось определить ID соревнования")
        comp_id = comp_match.group(1)

        # Запускаем volleystats
        cmd = ["volleystats", "--fed", fed, "--comp", comp_id]
        subprocess.run(cmd, capture_output=True, text=True)

        # Если папка data не создалась или пуста, возвращаем пустой DataFrame с правильными колонками
        if not os.path.exists("data"):
            return pd.DataFrame(columns=['Команда', 'Сеты', 'Мячи']), pd.DataFrame()
        
        files = [f for f in os.listdir("data") if f.endswith('.csv')]
        if not files:
            return pd.DataFrame(columns=['Команда', 'Сеты', 'Мячи']), pd.DataFrame()
        
        team_stats = {}
        for f in files:
            df = pd.read_csv(os.path.join("data", f))
            # Определяем название команды (из файла или из колонки team_name)
            if df.empty:
                continue
            if 'team_name' in df.columns:
                team = df['team_name'].iloc[0]
            else:
                team = f.replace('.csv', '')
            
            # Суммируем сеты и очки
            sets_won = df['sets_won'].sum() if 'sets_won' in df.columns else 0
            sets_lost = df['sets_lost'].sum() if 'sets_lost' in df.columns else 0
            points_won = df['points_won'].sum() if 'points_won' in df.columns else 0
            points_lost = df['points_lost'].sum() if 'points_lost' in df.columns else 0
            
            team_stats[team] = {
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'points_won': points_won,
                'points_lost': points_lost
            }
        
        if not team_stats:
            return pd.DataFrame(columns=['Команда', 'Сеты', 'Мячи']), pd.DataFrame()
        
        # Формируем DataFrame в едином формате
        df_stats = pd.DataFrame.from_dict(team_stats, orient='index')
        df_stats = df_stats.reset_index().rename(columns={'index': 'Команда'})
        df_stats['Сеты'] = df_stats['sets_won'].astype(str) + ':' + df_stats['sets_lost'].astype(str)
        df_stats['Мячи'] = df_stats['points_won'].astype(str) + ':' + df_stats['points_lost'].astype(str)
        df_stats = df_stats.sort_values('sets_won', ascending=False)
        return df_stats[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        # Автоматический поиск личных встреч для Data Project отключён
        print("[DEBUG] Личные встречи для Data Project вводятся вручную")
        return pd.DataFrame()
