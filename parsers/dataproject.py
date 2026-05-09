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

        cmd = ["volleystats", "--fed", fed, "--comp", comp_id]
        subprocess.run(cmd, capture_output=True, text=True)

        if not os.path.exists("data"):
            return pd.DataFrame(), pd.DataFrame()
        files = [f for f in os.listdir("data") if f.endswith('.csv')]
        if not files:
            return pd.DataFrame(), pd.DataFrame()
        df_list = [pd.read_csv(os.path.join("data", f)) for f in files]
        combined = pd.concat(df_list, ignore_index=True)
        return combined, pd.DataFrame()

    def fetch_head_to_head(self, url: str, team1: str, team2: str):
        # Автоматический поиск личных встреч для Data Project отключён
        print("[DEBUG] Личные встречи для Data Project вводятся вручную")
        return pd.DataFrame()
