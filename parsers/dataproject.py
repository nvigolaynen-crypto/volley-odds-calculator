import subprocess
import os
import re
import pandas as pd
import glob
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str):
        fed = self._extract_fed_from_url(url)
        comp_id = self._extract_comp_id_from_url(url)
        if not fed or not comp_id:
            raise ValueError("Не удалось определить fed или comp_id из URL")

        os.makedirs("temp_dp", exist_ok=True)
        original_dir = os.getcwd()
        os.chdir("temp_dp")

        try:
            cmd = ["volleystats", "--fed", fed, "--comp", comp_id]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"volleystats ошибка: {result.stderr}")

            if not os.path.exists("data"):
                raise FileNotFoundError("Папка data не создана")

            os.chdir("data")
            csv_files = glob.glob("*.csv")
            if not csv_files:
                raise FileNotFoundError("CSV файлы не найдены")

            team_stats = {}
            for file in csv_files:
                df = pd.read_csv(file)
                if 'team_name' not in df.columns:
                    continue
                team = df['team_name'].iloc[0]
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
                raise ValueError("Нет данных о командах")

            df_stats = pd.DataFrame.from_dict(team_stats, orient='index')
            df_stats = df_stats.reset_index().rename(columns={'index': 'Команда'})
            df_stats['Сеты'] = df_stats['sets_won'].astype(str) + ':' + df_stats['sets_lost'].astype(str)
            df_stats['Мячи'] = df_stats['points_won'].astype(str) + ':' + df_stats['points_lost'].astype(str)
            df_stats = df_stats.sort_values('sets_won', ascending=False)
            return df_stats[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()

        finally:
            os.chdir(original_dir)
            import shutil
            shutil.rmtree("temp_dp", ignore_errors=True)

    def _extract_fed_from_url(self, url: str) -> str:
        match = re.search(r'https?://([a-z]+)-web\.dataproject\.com', url)
        return match.group(1) if match else None

    def _extract_comp_id_from_url(self, url: str) -> str:
        match = re.search(r'[?&]ID=(\d+)', url)
        return match.group(1) if match else None
