import subprocess
import pandas as pd
import os
import glob
from .base_parser import BaseParser

class DataProjectParser(BaseParser):
    def fetch_stats(self, url: str):
        """
        Для DataProject URL не используется напрямую. Пользователь должен ввести fed и comp_id.
        Этот метод будет вызван из app.py с параметрами, переданными через session_state.
        """
        # Здесь мы не можем определить fed/comp из URL автоматически, поэтому ожидаем,
        # что в app.py перед вызовом будут заданы fed и comp_id.
        # Для простоты сейчас вернём пустой DataFrame, но в app.py мы реализуем отдельную ветку.
        return pd.DataFrame(), pd.DataFrame()
    
    def fetch_by_ids(self, fed: str, comp_id: str = None, match_id: str = None):
        command = ["volleystats", "--fed", fed]
        if comp_id:
            command.extend(["--comp", comp_id])
        elif match_id:
            command.extend(["--match", match_id])
        else:
            raise ValueError("Укажите comp_id или match_id")
        
        subprocess.run(command, check=True, capture_output=True, text=True)
        all_files = glob.glob("data/*.csv")
        if not all_files:
            return pd.DataFrame()
        df_list = [pd.read_csv(f) for f in all_files]
        combined_df = pd.concat(df_list, ignore_index=True)
        return combined_df
