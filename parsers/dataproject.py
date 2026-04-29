import subprocess
import pandas as pd
import os
import glob
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, fed: str, comp_id: str = None, match_id: str = None):
        """
        Запускает volleystats для сбора статистики и возвращает DataFrame.
        """
        command = ["volleystats", "--fed", fed]
        if comp_id:
            command.extend(["--comp", comp_id])
        elif match_id:
            command.extend(["--match", match_id])
        else:
            raise ValueError("Укажите comp_id или match_id")

        try:
            # Запускаем volleystats
            subprocess.run(command, check=True, capture_output=True, text=True)

            # Ищем созданные CSV-файлы в папке data
            all_files = glob.glob("data/*.csv")
            if not all_files:
                return pd.DataFrame(), pd.DataFrame()

            # Читаем и объединяем все CSV в один DataFrame
            df_list = [pd.read_csv(f) for f in all_files]
            combined_df = pd.concat(df_list, ignore_index=True)

            return combined_df, pd.DataFrame()
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при выполнении volleystats: {e}")
            return pd.DataFrame(), pd.DataFrame()