import subprocess
import os
import re
import pandas as pd
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str):
        """
        Универсальный парсер для сайтов Data Project.
        Автоматически определяет федерацию (fed) и ID турнира (comp) из URL.
        Запускает volleystats для сбора статистики, затем агрегирует данные по командам.
        """
        # 1. Извлекаем fed и comp_id из URL
        fed = self._extract_fed_from_url(url)
        comp_id = self._extract_comp_id_from_url(url)
        if not fed or not comp_id:
            raise ValueError("Не удалось определить федерацию или ID соревнования из URL")

        # 2. Создаём временную директорию для данных
        os.makedirs("temp_data", exist_ok=True)
        original_dir = os.getcwd()
        os.chdir("temp_data")

        try:
            # 3. Запускаем volleystats
            command = ["volleystats", "--fed", fed, "--comp", comp_id]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"volleystats завершился с ошибкой: {result.stderr}")

            # 4. Собираем все CSV-файлы
            all_files = [f for f in os.listdir(".") if f.endswith('.csv')]
            if not all_files:
                raise ValueError("volleystats не создал CSV-файлов")

            # 5. Агрегируем статистику по командам
            team_stats = {}
            for file in all_files:
                df = pd.read_csv(file)
                # Определяем, о какой команде файл (по имени файла или по колонкам)
                if 'team_name' in df.columns:
                    team_name = df['team_name'].iloc[0] if not df.empty else None
                else:
                    # Пробуем извлечь из названия файла (обычно формат: fed_comp_teamname.csv)
                    team_name = file.replace('.csv', '').split('_')[-1]
                if not team_name:
                    continue

                # Ищем колонки с очками и сетами
                points_col = None
                sets_col = None
                for col in df.columns:
                    if 'point' in col.lower() or 'очк' in col.lower():
                        points_col = col
                    if 'set' in col.lower() or 'сет' in col.lower():
                        sets_col = col

                if points_col and sets_col:
                    # Суммируем итоги
                    total_points = df[points_col].sum()
                    total_sets_won = df[sets_col].sum()
                    # Пока не знаем сколько проиграно, потом доработаем
                    if team_name not in team_stats:
                        team_stats[team_name] = {'sets_won': 0, 'sets_lost': 0, 'points_won': 0, 'points_lost': 0}
                    team_stats[team_name]['points_won'] += total_points
                    team_stats[team_name]['sets_won'] += total_sets_won

            # 6. Формируем DataFrame
            df_stats = pd.DataFrame.from_dict(team_stats, orient='index')
            df_stats = df_stats.reset_index().rename(columns={'index': 'Команда'})
            df_stats['Сеты'] = df_stats['sets_won'].astype(str) + ':' + df_stats['sets_lost'].astype(str)
            df_stats['Мячи'] = df_stats['points_won'].astype(str) + ':' + df_stats['points_lost'].astype(str)
            df_stats = df_stats.sort_values('sets_won', ascending=False)

            return df_stats[['Команда', 'Сеты', 'Мячи']], pd.DataFrame()

        finally:
            os.chdir(original_dir)
            # Очищаем временную папку
            import shutil
            shutil.rmtree("temp_data", ignore_errors=True)

    def _extract_fed_from_url(self, url: str) -> str:
        """Извлекает аббревиатуру федерации из URL."""
        match = re.search(r'https?://([a-z]+)-web\.dataproject\.com', url)
        return match.group(1) if match else None

    def _extract_comp_id_from_url(self, url: str) -> str:
        """Извлекает ID соревнования из URL."""
        match = re.search(r'[?&]ID=(\d+)', url)
        return match.group(1) if match else None
