import streamlit as st
import pandas as pd
import re
import math
import json
import requests
from bs4 import BeautifulSoup

# ==================== КОРРЕКТИРОВКИ ФОРЫ ====================

def adjust_handicap_men_home(handicap: float) -> float:
    if handicap <= -43: return handicap * 1.3
    elif handicap <= -34.5: return handicap * 1.38
    elif handicap <= -17.5: return handicap * 1.48
    elif handicap <= -12.5: return handicap * 1.7
    elif handicap <= -9.5: return handicap * 1.9
    elif handicap <= -7.5: return handicap * 2.0
    elif handicap <= -6.5: return handicap * 2.2
    elif handicap <= -5.5: return handicap * 1.94
    elif handicap <= -4.5: return handicap * 1.9
    elif handicap <= -3.5: return handicap * 1.8
    elif handicap <= -2.75: return handicap * 2.1
    elif handicap <= -2.25: return handicap * 1.75
    elif handicap <= -1.75: return handicap * 1.0
    elif handicap <= -1.25: return handicap * 0.5
    elif handicap <= -0.75: return handicap * 0.0
    elif handicap < 1.25: return handicap + 2.5
    elif handicap < 1.75: return handicap * 3.5
    elif handicap < 2.75: return handicap * 3.7
    elif handicap < 3.5: return handicap * 3.6
    elif handicap < 4.5: return handicap * 3.2
    elif handicap < 6.5: return handicap * 2.7
    elif handicap < 7.5: return handicap * 2.5
    elif handicap < 9.5: return handicap * 2.4
    elif handicap < 10.5: return handicap * 2.3
    elif handicap < 14.5: return handicap * 2.2
    elif handicap < 17.5: return handicap * 2.0
    elif handicap < 21.5: return handicap * 1.68
    elif handicap < 34.5: return handicap * 1.65
    elif handicap < 43: return handicap * 1.38
    else: return handicap * 1.3

def adjust_handicap_men_neutral(handicap: float) -> float:
    if handicap <= -43: return handicap * 1.3
    elif handicap <= -34.5: return handicap * 1.38
    elif handicap <= -21.5: return handicap * 1.57
    elif handicap <= -17.5: return handicap * 1.58
    elif handicap <= -14.5: return handicap * 1.85
    elif handicap <= -12.5: return handicap * 1.95
    elif handicap <= -10.5: return handicap * 2.05
    elif handicap <= -9.5: return handicap * 2.1
    elif handicap <= -7.5: return handicap * 2.2
    elif handicap <= -4.5: return handicap * 2.3
    elif handicap <= -3.5: return handicap * 2.5
    elif handicap <= -2.75: return handicap * 2.85
    elif handicap <= -2.25: return handicap * 2.73
    elif handicap <= -1.85: return handicap * 2.35
    elif handicap <= -1.65: return handicap * 1.8
    elif handicap <= -1.25: return handicap * 1.48
    elif handicap < 1.25: return handicap * 1.0
    elif handicap < 1.6: return handicap * 1.48
    elif handicap < 1.85: return handicap * 1.8
    elif handicap < 2.25: return handicap * 2.35
    elif handicap < 2.75: return handicap * 2.73
    elif handicap < 3.5: return handicap * 2.85
    elif handicap < 4.5: return handicap * 2.5
    elif handicap < 7.5: return handicap * 2.3
    elif handicap < 9.5: return handicap * 2.2
    elif handicap < 10.5: return handicap * 2.1
    elif handicap < 12.5: return handicap * 2.05
    elif handicap < 14.5: return handicap * 1.95
    elif handicap < 17.5: return handicap * 1.85
    elif handicap < 21.5: return handicap * 1.58
    elif handicap < 34.5: return handicap * 1.57
    elif handicap < 43: return handicap * 1.38
    else: return handicap * 1.3

def adjust_handicap_women_home(handicap: float) -> float:
    if handicap <= -43: return handicap * 1.3
    elif handicap <= -38.5: return handicap * 1.38
    elif handicap <= -27.5: return handicap * 1.5
    elif handicap <= -25.5: return handicap * 1.54
    elif handicap <= -17.5: return handicap * 1.58
    elif handicap <= -16.5: return handicap * 1.75
    elif handicap <= -14.5: return handicap * 1.8
    elif handicap <= -10.5: return handicap * 2.0
    elif handicap <= -4.5: return handicap * 2.2
    elif handicap <= -3.75: return handicap * 2.1
    elif handicap <= -3.25: return handicap * 1.75
    elif handicap <= -2.75: return handicap * 1.5
    elif handicap <= -2.25: return handicap * 1.0
    elif handicap <= -1.75: return handicap * 0.5
    elif handicap <= -1.5: return handicap * 0.0
    elif handicap <= -1.25: return handicap * -0.6
    elif handicap <= -0.75: return handicap * -3
    elif handicap < 0: return handicap + 3.5
    elif handicap == 0: return 3.5
    elif handicap < 0.75: return handicap + 3.5
    elif handicap < 1.25: return handicap + 3.5
    elif handicap < 1.75: return handicap * 3.5
    elif handicap < 2.25: return handicap * 4.0
    elif handicap < 2.75: return handicap * 4.8
    elif handicap < 3.5: return handicap * 4.0
    elif handicap < 4.5: return handicap * 3.3
    elif handicap < 5.5: return handicap * 2.5
    elif handicap < 6.5: return handicap * 2.5
    elif handicap < 7.5: return handicap * 2.5
    elif handicap < 10.5: return handicap * 2.4
    elif handicap < 11.5: return handicap * 2.3
    elif handicap < 12.5: return handicap * 2.1
    elif handicap < 14.5: return handicap * 1.9
    elif handicap < 23.5: return handicap * 1.8
    elif handicap < 29.5: return handicap * 1.62
    elif handicap < 38.5: return handicap * 1.5
    elif handicap < 43: return handicap * 1.38
    else: return handicap * 1.3

def adjust_handicap_women_neutral(handicap: float) -> float:
    if handicap <= -43: return handicap * 1.3
    elif handicap <= -38.5: return handicap * 1.38
    elif handicap <= -29.5: return handicap * 1.5
    elif handicap <= -27.5: return handicap * 1.56
    elif handicap <= -25.5: return handicap * 1.58
    elif handicap <= -23.5: return handicap * 1.6
    elif handicap <= -17.5: return handicap * 1.69
    elif handicap <= -14.5: return handicap * 1.8
    elif handicap <= -12.5: return handicap * 1.95
    elif handicap <= -11.5: return handicap * 2.05
    elif handicap <= -10.5: return handicap * 2.15
    elif handicap <= -6.5: return handicap * 2.3
    elif handicap <= -5.5: return handicap * 2.4
    elif handicap <= -4.5: return handicap * 2.5
    elif handicap <= -3.5: return handicap * 2.8
    elif handicap <= -2.25: return handicap * 2.9
    elif handicap <= -1.85: return handicap * 2.25
    elif handicap <= -1.65: return handicap * 1.8
    elif handicap <= -1.25: return handicap * 1.48
    elif handicap < 1.25: return handicap * 1.0
    elif handicap < 1.6: return handicap * 1.48
    elif handicap < 1.85: return handicap * 1.8
    elif handicap < 2.25: return handicap * 2.25
    elif handicap < 3.5: return handicap * 2.9
    elif handicap < 4.5: return handicap * 2.8
    elif handicap < 5.5: return handicap * 2.5
    elif handicap < 6.5: return handicap * 2.4
    elif handicap < 10.5: return handicap * 2.3
    elif handicap < 11.5: return handicap * 2.15
    elif handicap < 12.5: return handicap * 2.05
    elif handicap < 14.5: return handicap * 1.95
    elif handicap < 17.5: return handicap * 1.8
    elif handicap < 23.5: return handicap * 1.69
    elif handicap < 25.5: return handicap * 1.6
    elif handicap < 27.5: return handicap * 1.58
    elif handicap < 29.5: return handicap * 1.56
    elif handicap < 38.5: return handicap * 1.5
    elif handicap < 43: return handicap * 1.38
    else: return handicap * 1.3

def adjust_handicap_men_2(handicap: float) -> float:
    if handicap <= -33.5: return handicap * 1.33
    elif handicap <= -19.5: return handicap * 1.42
    elif handicap <= -14.5: return handicap * 1.25
    elif handicap <= -12.5: return handicap * 1.5
    elif handicap <= -10.5: return handicap * 1.68
    elif handicap <= -9.5: return handicap * 1.45
    elif handicap <= -8.5: return handicap * 1.4
    elif handicap <= -6.5: return handicap * 1.56
    elif handicap <= -5.5: return handicap * 1.6
    elif handicap <= -4.5: return handicap * 2.1
    elif handicap <= -3.5: return handicap * 2.4
    elif handicap <= -2.75: return handicap * 2.5
    elif handicap <= -2.25: return handicap * 1.9
    elif handicap <= -1.5: return handicap * 1.44
    elif handicap <= -0.5: return handicap * 2.0
    elif handicap < 0: return handicap - 0.75
    elif handicap == 0: return 0.0
    elif handicap < 0.5: return handicap + 0.75
    elif handicap < 1.5: return handicap * 2.0
    elif handicap < 2.25: return handicap * 1.44
    elif handicap < 2.75: return handicap * 1.9
    elif handicap < 3.5: return handicap * 2.5
    elif handicap < 4.5: return handicap * 2.4
    elif handicap < 5.5: return handicap * 2.1
    elif handicap < 6.5: return handicap * 1.6
    elif handicap < 8.5: return handicap * 1.56
    elif handicap < 9.5: return handicap * 1.4
    elif handicap < 10.5: return handicap * 1.45
    elif handicap < 12.5: return handicap * 1.68
    elif handicap < 14.5: return handicap * 1.5
    elif handicap < 19.5: return handicap * 1.25
    elif handicap < 33.5: return handicap * 1.42
    else: return handicap * 1.33

def adjust_handicap_women_2(handicap: float) -> float:
    if handicap <= -26.5: return handicap * 1.33
    elif handicap <= -19.5: return handicap * 1.42
    elif handicap <= -17.5: return handicap * 1.65
    elif handicap <= -14.5: return handicap * 1.4
    elif handicap <= -13.5: return handicap * 1.5
    elif handicap <= -12.5: return handicap * 1.7
    elif handicap <= -11.5: return handicap * 1.73
    elif handicap <= -9.5: return handicap * 1.9
    elif handicap <= -8.5: return handicap * 1.83
    elif handicap <= -5.5: return handicap * 1.83
    elif handicap <= -4.5: return handicap * 1.87
    elif handicap <= -3.5: return handicap * 2.8
    elif handicap <= -2.5: return handicap * 3.0
    elif handicap <= -1.75: return handicap * 4.2
    elif handicap < -1.25: return handicap * 3.75
    elif handicap < 0: return handicap - 0.0
    elif handicap == 0: return 0.0
    elif handicap <= 1.25: return handicap + 0.0
    elif handicap < 1.75: return handicap * 3.75
    elif handicap <= 2.5: return handicap * 4.2
    elif handicap < 3.5: return handicap * 3.0
    elif handicap < 4.5: return handicap * 2.8
    elif handicap < 5.5: return handicap * 1.87
    elif handicap < 8.5: return handicap * 1.83
    elif handicap < 9.5: return handicap * 1.83
    elif handicap < 11.5: return handicap * 1.9
    elif handicap < 12.5: return handicap * 1.73
    elif handicap < 13.5: return handicap * 1.7
    elif handicap < 14.5: return handicap * 1.5
    elif handicap < 17.5: return handicap * 1.4
    elif handicap < 19.5: return handicap * 1.65
    elif handicap < 26.5: return handicap * 1.42
    else: return handicap * 1.33

def adjust_handicap_men_3(handicap: float) -> float:
    if handicap <= -20.5: return handicap * 1.3
    elif handicap <= -18.5: return handicap * 1.6
    elif handicap <= -9.5: return handicap * 1.7
    elif handicap <= -7.5: return handicap * 1.5
    elif handicap <= -6.5: return handicap * 2.0
    elif handicap <= -5.5: return handicap * 2.55
    elif handicap <= -4.5: return handicap * 2.4
    elif handicap <= -3.75: return handicap * 2.2
    elif handicap <= -3.25: return handicap * 1.85
    elif handicap <= -1.5: return handicap * 1.5
    elif handicap < 0: return handicap - 5.0
    elif handicap == 0: return 0.0
    elif handicap < 1.5: return handicap + 5.0
    elif handicap < 3.25: return handicap * 1.5
    elif handicap <= 3.75: return handicap * 1.85
    elif handicap < 4.5: return handicap * 2.2
    elif handicap < 5.5: return handicap * 2.4
    elif handicap < 6.5: return handicap * 2.55
    elif handicap < 7.5: return handicap * 2.0
    elif handicap < 9.5: return handicap * 1.5
    elif handicap < 18.5: return handicap * 1.7
    elif handicap < 20.5: return handicap * 1.6
    else: return handicap * 1.3

def adjust_handicap_women_3(handicap: float) -> float:
    if handicap <= -28.5: return handicap * 1.4
    elif handicap <= -14.5: return handicap * 1.55
    elif handicap <= -13.5: return handicap * 1.65
    elif handicap <= -12.5: return handicap * 1.75
    elif handicap <= -11.5: return handicap * 1.85
    elif handicap <= -10.5: return handicap * 2.1
    elif handicap <= -9.5: return handicap * 2.6
    elif handicap <= -8.5: return handicap * 2.6
    elif handicap <= -7.5: return handicap * 1.42
    elif handicap <= -6.5: return handicap * 1.42
    elif handicap <= -5.5: return handicap * 1.42
    elif handicap <= -4.5: return handicap * 1.42
    elif handicap <= -3.5: return handicap * 1.6
    elif handicap <= -2.75: return handicap * 0.63
    elif handicap <= -2.25: return handicap - 2.5
    elif handicap < 0: return handicap - 5.0
    elif handicap == 0: return 0.0
    elif handicap < 2.25: return handicap + 5.0
    elif handicap < 2.75: return handicap + 2.5
    elif handicap <= 3.5: return handicap * 1.63
    elif handicap < 4.5: return handicap * 1.6
    elif handicap < 5.5: return handicap * 1.42
    elif handicap < 6.5: return handicap * 1.42
    elif handicap < 7.5: return handicap * 1.42
    elif handicap < 8.5: return handicap * 1.42
    elif handicap < 9.5: return handicap * 2.6
    elif handicap < 10.5: return handicap * 2.6
    elif handicap < 11.5: return handicap * 2.1
    elif handicap < 12.5: return handicap * 1.85
    elif handicap < 13.5: return handicap * 1.75
    elif handicap < 14.5: return handicap * 1.65
    elif handicap < 28.5: return handicap * 1.55
    else: return handicap * 1.4

# ==================== ОБЩИЕ ФУНКЦИИ ====================

def prob_win_match(p: float, best_of: int = 5) -> float:
    if p <= 0: return 0.0
    if p >= 1: return 1.0
    q = 1 - p
    if best_of == 3:
        return p**2 * (1 + 2*q)
    else:
        return 10 * p**3 * q**2 + 5 * p**4 * q + p**5

def calculate_raw_handicap(h_sets_w, h_sets_l, h_pts_w, h_pts_l, h_matches,
                           a_sets_w, a_sets_l, a_pts_w, a_pts_l, a_matches):
    if h_matches is None or a_matches is None or h_matches <= 0 or a_matches <= 0:
        return None
    home_avg_scored = h_pts_w / h_matches
    home_avg_conceded = h_pts_l / h_matches
    away_avg_scored = a_pts_w / a_matches
    away_avg_conceded = a_pts_l / a_matches
    expected_home = (home_avg_scored + away_avg_conceded) / 2
    expected_away = (away_avg_scored + home_avg_conceded) / 2
    return expected_home - expected_away

def detect_gender_by_url(url: str) -> str:
    url_lower = url.lower()
    if any(x in url_lower for x in ['femminile', 'women', 'kadinlar', 'liga kobiet', 'womens', 'legavolleyfemminile']):
        return "Женщины"
    if any(x in url_lower for x in ['superlega', 'plusliga', 'legavolley.it', 'volley.ru']):
        return "Мужчины"
    return None

# ==================== ПАРСЕРЫ ТАБЛИЦ ====================

def parse_table_to_df(data_source, file_type=None):
    def to_int(val):
        if pd.isna(val): return None
        s = str(val).strip()
        s = s.replace('.', '')
        s = s.replace(',', '.')
        try:
            return int(float(s))
        except:
            return None
    def clean_team_name(name):
        name = re.sub(r'^\d+\s+', '', name)
        name = re.sub(r'^[\d\.]+\s+', '', name)
        return name.strip()
    if file_type == 'csv':
        content = data_source.getvalue().decode('utf-8')
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines: return None
        delimiter = None
        for line in lines[:5]:
            if ';' in line: delimiter = ';'; break
            if ',' in line: delimiter = ','; break
        if delimiter is None: delimiter = ','
        keywords = {
            'team': ['squadra', 'team', 'drużyna', 'takım adı', 'nome', 'команда'],
            'matches': ['g', 'o', 'mecze', 'giocate', 'partite', 'матчей', 'rozegr'],
            'sets_w': ['sv', 'a', 'wygr', 'vinti', 'выигр', 'set_w'],
            'sets_l': ['sp', 'v', 'przegr', 'persi', 'проигр', 'set_l'],
            'pts_w': ['pf', 'asp', 'punkty wygr', 'fatti', 'набрано', 'punti fatti'],
            'pts_l': ['ps', 'vsp', 'punkty przegr', 'subiti', 'пропущено', 'punti subiti']
        }
        header_idx = None
        for i, line in enumerate(lines):
            line_low = line.lower()
            has_team = any(k in line_low for k in keywords['team'])
            has_matches = any(k in line_low for k in keywords['matches'])
            has_sets_w = any(k in line_low for k in keywords['sets_w'])
            has_sets_l = any(k in line_low for k in keywords['sets_l'])
            if has_team and has_matches and has_sets_w and has_sets_l:
                header_idx = i
                break
        if header_idx is None: header_idx = 0
        header_parts = lines[header_idx].split(delimiter)
        header_parts = [p.strip('"').strip() for p in header_parts]
        col_team = col_matches = col_sets_w = col_sets_l = col_pts_w = col_pts_l = None
        for idx, col in enumerate(header_parts):
            col_low = col.lower()
            if col_team is None and any(k in col_low for k in keywords['team']): col_team = idx
            if col_matches is None and any(k in col_low for k in keywords['matches']): col_matches = idx
            if col_sets_w is None and any(k in col_low for k in keywords['sets_w']): col_sets_w = idx
            if col_sets_l is None and any(k in col_low for k in keywords['sets_l']): col_sets_l = idx
            if col_pts_w is None and any(k in col_low for k in keywords['pts_w']): col_pts_w = idx
            if col_pts_l is None and any(k in col_low for k in keywords['pts_l']): col_pts_l = idx
        if col_matches is None or col_sets_w is None or col_sets_l is None:
            for idx, col in enumerate(header_parts):
                col_up = col.strip().upper()
                if col_up == 'O': col_matches = idx
                if col_up == 'A': col_sets_w = idx
                if col_up == 'V': col_sets_l = idx
                if col_up == 'ASP': col_pts_w = idx
                if col_up == 'VSP': col_pts_l = idx
        if col_team is None or col_matches is None or col_sets_w is None or col_sets_l is None:
            return None
        rows = []
        for line in lines[header_idx+1:]:
            parts = line.split(delimiter)
            parts = [p.strip('"').strip() for p in parts]
            if len(parts) <= max(col_team, col_matches, col_sets_w, col_sets_l): continue
            team = parts[col_team].strip()
            if not team: continue
            team = clean_team_name(team)
            matches = to_int(parts[col_matches])
            sets_w = to_int(parts[col_sets_w])
            sets_l = to_int(parts[col_sets_l])
            if sets_w is None or sets_l is None: continue
            pts_w = to_int(parts[col_pts_w]) if col_pts_w is not None and col_pts_w < len(parts) else 0
            pts_l = to_int(parts[col_pts_l]) if col_pts_l is not None and col_pts_l < len(parts) else 0
            if pts_w is None: pts_w = 0
            if pts_l is None: pts_l = 0
            rows.append({'Команда': team, 'Сеты': f"{sets_w}:{sets_l}", 'Мячи': f"{pts_w}:{pts_l}", 'Матчи': matches})
        if rows: return pd.DataFrame(rows)
        return None
    elif file_type == 'xlsx':
        try:
            df_raw = pd.read_excel(data_source, header=None, engine='openpyxl')
        except Exception as e:
            st.error(f"Ошибка чтения Excel: {e}")
            return None
        keywords = {
            'team': ['squadra', 'team', 'drużyna', 'takım adı', 'nome', 'команда'],
            'matches': ['g', 'o', 'mecze', 'giocate', 'partite', 'матчей', 'rozegr', 'match'],
            'sets_w': ['sv', 'a', 'wygr', 'vinti', 'выигр', 'set_w', 'sets won'],
            'sets_l': ['sp', 'v', 'przegr', 'persi', 'проигр', 'set_l', 'sets lost']
        }
        header_idx = None
        for idx, row in df_raw.iterrows():
            row_text = ' '.join(str(cell).lower() for cell in row if pd.notna(cell))
            has_team = any(k in row_text for k in keywords['team'])
            has_matches = any(k in row_text for k in keywords['matches'])
            has_sets_w = any(k in row_text for k in keywords['sets_w'])
            has_sets_l = any(k in row_text for k in keywords['sets_l'])
            if has_team and has_matches and has_sets_w and has_sets_l:
                header_idx = idx
                break
        if header_idx is None: header_idx = 0
        header_row = df_raw.iloc[header_idx].fillna('').astype(str)
        col_team = col_matches = col_sets_w = col_sets_l = col_pts_w = col_pts_l = None
        for i, val in enumerate(header_row):
            val_low = val.lower()
            if col_team is None and any(k in val_low for k in keywords['team']): col_team = i
            if col_matches is None and any(k in val_low for k in keywords['matches']): col_matches = i
            if col_sets_w is None and any(k in val_low for k in keywords['sets_w']): col_sets_w = i
            if col_sets_l is None and any(k in val_low for k in keywords['sets_l']): col_sets_l = i
            if 'fatti' in val_low or 'набрано' in val_low or 'punkty wygr' in val_low: col_pts_w = i
            if 'subiti' in val_low or 'пропущено' in val_low or 'punkty przegr' in val_low: col_pts_l = i
        for i, val in enumerate(header_row):
            val_up = str(val).strip().upper()
            if val_up == 'O': col_matches = i
            if val_up == 'A': col_sets_w = i
            if val_up == 'V': col_sets_l = i
            if val_up == 'ASP': col_pts_w = i
            if val_up == 'VSP': col_pts_l = i
        if col_team is None or col_matches is None or col_sets_w is None or col_sets_l is None:
            st.error("Не удалось определить колонки в Excel")
            return None
        rows = []
        for idx in range(header_idx+1, len(df_raw)):
            row = df_raw.iloc[idx]
            if all(pd.isna(cell) for cell in row): continue
            team = str(row.iloc[col_team]).strip()
            if not team or team == 'nan': continue
            team = clean_team_name(team)
            matches = to_int(row.iloc[col_matches]) if pd.notna(row.iloc[col_matches]) else None
            if matches is None: continue
            sets_w = to_int(row.iloc[col_sets_w]) if pd.notna(row.iloc[col_sets_w]) else None
            sets_l = to_int(row.iloc[col_sets_l]) if pd.notna(row.iloc[col_sets_l]) else None
            if sets_w is None or sets_l is None: continue
            pts_w = to_int(row.iloc[col_pts_w]) if col_pts_w is not None and pd.notna(row.iloc[col_pts_w]) else 0
            pts_l = to_int(row.iloc[col_pts_l]) if col_pts_l is not None and pd.notna(row.iloc[col_pts_l]) else 0
            if pts_w is None: pts_w = 0
            if pts_l is None: pts_l = 0
            rows.append({'Команда': team, 'Сеты': f"{sets_w}:{sets_l}", 'Мячи': f"{pts_w}:{pts_l}", 'Матчи': matches})
        if rows: return pd.DataFrame(rows)
        return None
    else:
        return parse_text_to_df(data_source)

def parse_text_to_df(text: str) -> pd.DataFrame:
    def parse_pair(s):
        if ':' not in s: return 0,0
        parts = s.split(':')
        if len(parts)!=2: return 0,0
        try:
            return int(float(parts[0])), int(float(parts[1]))
        except:
            return 0,0
    lines = text.strip().split('\n')
    data = []
    for line in lines:
        line=line.strip()
        if not line: continue
        if ';' in line:
            parts = line.split(';')
            if len(parts)>=3:
                team=parts[0].strip()
                sets=parts[1].strip()
                points=parts[2].strip()
                matches=None
                if len(parts)>=4 and parts[3].strip().isdigit():
                    matches=int(parts[3].strip())
                w,l=parse_pair(sets)
                pw,pl=parse_pair(points)
                if w==0 and l==0: continue
                data.append({'Команда':team,'Сеты':f"{w}:{l}",'Мячи':f"{pw}:{pl}",'Матчи':matches})
            continue
        tokens = re.split(r'\s+',line)
        numbers=[]; team_parts=[]
        for tok in tokens:
            if re.match(r'^[\d\.,]+$',tok): numbers.append(tok)
            else: team_parts.append(tok)
        if len(numbers)<4: continue
        team=' '.join(team_parts).strip()
        if not team: continue
        try:
            w=int(float(numbers[0]))
            l=int(float(numbers[1]))
            pw=int(float(numbers[2].replace('.','').replace(',','.')))
            pl=int(float(numbers[3].replace('.','').replace(',','.')))
            data.append({'Команда':team,'Сеты':f"{w}:{l}",'Мячи':f"{pw}:{pl}",'Матчи':None})
        except: continue
    if data: return pd.DataFrame(data)
    return None

# ==================== ПАРСЕРЫ DATA PROJECT ====================

def extract_team_data_from_dataproject_table(table_html: str) -> dict:
    soup = BeautifulSoup(table_html, 'html.parser')
    rows = soup.find_all('tr', class_=re.compile(r'RG_Standing_Main_AltBackColor'))
    if not rows:
        rows = soup.find_all('tr')
        rows = [row for row in rows if row.find('span', id=re.compile(r'TeamName'))]
    teams = {}
    for row in rows:
        team_span = row.find('span', id=re.compile(r'TeamName'))
        if not team_span: continue
        team = team_span.get_text(strip=True)
        if not team: continue
        matches_span = row.find('span', id=re.compile(r'MatchesPlayed'))
        matches = int(matches_span.get_text(strip=True)) if matches_span and matches_span.get_text(strip=True).isdigit() else None
        sets_won_span = row.find('span', id=re.compile(r'SetsWon'))
        sets_lost_span = row.find('span', id=re.compile(r'SetsLost'))
        sets_won = int(sets_won_span.get_text(strip=True)) if sets_won_span else 0
        sets_lost = int(sets_lost_span.get_text(strip=True)) if sets_lost_span else 0
        pts_won_span = row.find('span', id=re.compile(r'PuntiFatti'))
        pts_lost_span = row.find('span', id=re.compile(r'PuntiSubiti'))
        pts_won = int(pts_won_span.get_text(strip=True)) if pts_won_span else 0
        pts_lost = int(pts_lost_span.get_text(strip=True)) if pts_lost_span else 0
        teams[team] = {'sets_w': sets_won, 'sets_l': sets_lost, 'pts_w': pts_won, 'pts_l': pts_lost, 'matches': matches}
    return teams

def extract_all_phases_from_dataproject_page(html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    phase_divs = soup.find_all('div', class_='rmpView')
    if not phase_divs:
        table = soup.find('table', class_='rgMasterTable')
        if table:
            return extract_team_data_from_dataproject_table(str(table))
        return {}
    combined = {}
    for phase_div in phase_divs:
        table = phase_div.find('table', class_='rgMasterTable')
        if not table: continue
        teams_data = extract_team_data_from_dataproject_table(str(table))
        for team, stats in teams_data.items():
            if team not in combined:
                combined[team] = {'sets_w': 0, 'sets_l': 0, 'pts_w': 0, 'pts_l': 0, 'matches': 0 if stats['matches'] is not None else None}
            combined[team]['sets_w'] += stats['sets_w']
            combined[team]['sets_l'] += stats['sets_l']
            combined[team]['pts_w'] += stats['pts_w']
            combined[team]['pts_l'] += stats['pts_l']
            if stats['matches'] is not None:
                if combined[team]['matches'] is None: combined[team]['matches'] = 0
                combined[team]['matches'] += stats['matches']
    return combined

def load_teams_from_url(url, combine_phases):
    if "dataproject.com" in url:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки: {e}"
        if combine_phases:
            combined_data = extract_all_phases_from_dataproject_page(resp.text)
        else:
            table = BeautifulSoup(resp.text, 'html.parser').find('table', class_='rgMasterTable')
            if not table:
                return None, "Таблица не найдена"
            combined_data = extract_team_data_from_dataproject_table(str(table))
        if not combined_data:
            return None, "Не удалось найти данные"
        rows = []
        for team, stats in combined_data.items():
            rows.append({
                'Команда': team,
                'Сеты': f"{stats['sets_w']}:{stats['sets_l']}",
                'Мячи': f"{stats['pts_w']}:{stats['pts_l']}",
                'Матчи': stats['matches'] if stats['matches'] is not None else None
            })
        return pd.DataFrame(rows), None
    else:
        return None, "URL не поддерживается (только DataProject)"

# ==================== STREAMLIT APP ====================

st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Session state
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None
if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}
if 'active_source' not in st.session_state:
    st.session_state.active_source = "auto"
if 'user_tables' not in st.session_state:
    st.session_state.user_tables = {}
if 'selected_user_table' not in st.session_state:
    st.session_state.selected_user_table = None
if 'detected_gender' not in st.session_state:
    st.session_state.detected_gender = None
if 'home_team' not in st.session_state:
    st.session_state.home_team = None
if 'away_team' not in st.session_state:
    st.session_state.away_team = None

# Sidebar
with st.sidebar:
    st.header("📁 Мои таблицы")
    col_exp, col_imp, col_clear = st.columns(3)
    with col_exp:
        if st.button("💾 Экспорт всех таблиц"):
            tables_json = json.dumps({name: df.to_dict(orient='records') for name, df in st.session_state.user_tables.items()})
            st.download_button("Скачать JSON", tables_json, file_name="volley_tables.json", mime="application/json")
    with col_imp:
        uploaded_json = st.file_uploader("📂 Импорт JSON", type=['json'], key="import_json")
        if uploaded_json:
            try:
                imported = json.load(uploaded_json)
                for name, data in imported.items():
                    df = pd.DataFrame(data)
                    if 'Команда' in df.columns and 'Сеты' in df.columns and 'Мячи' in df.columns:
                        st.session_state.user_tables[name] = df
                st.success(f"Импортировано {len(imported)} таблиц")
            except Exception as e:
                st.error(f"Ошибка импорта: {e}")
    with col_clear:
        if st.button("🗑️ Очистить все таблицы"):
            st.session_state.user_tables = {}
            st.rerun()
    with st.expander("➕ Новая таблица"):
        table_name = st.text_input("Название таблицы")
        upload_method = st.radio("Способ загрузки", ["Текстовый ввод", "CSV/Excel"])
        if upload_method == "Текстовый ввод":
            st.markdown("Формат: `Название;Сеты;Мячи` или `Название;Сеты;Мячи;Матчи`")
            text_data = st.text_area("Введите данные", height=200)
            if st.button("Создать таблицу"):
                df_new = parse_text_to_df(text_data)
                if df_new is not None:
                    st.session_state.user_tables[table_name] = df_new
                    st.success(f"Таблица '{table_name}' создана ({len(df_new)} команд)")
                    st.rerun()
                else:
                    st.error("Не удалось распознать данные")
        else:
            uploaded_file = st.file_uploader("CSV или Excel", type=['csv', 'xlsx'])
            if uploaded_file and st.button("Создать таблицу"):
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_new = parse_table_to_df(uploaded_file, 'csv')
                    else:
                        df_new = parse_table_to_df(uploaded_file, 'xlsx')
                    if df_new is not None and not df_new.empty:
                        st.session_state.user_tables[table_name] = df_new
                        st.success(f"Таблица '{table_name}' создана ({len(df_new)} команд)")
                        st.rerun()
                    else:
                        st.error("Не удалось распознать файл")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    if st.session_state.user_tables:
        st.subheader("Доступные таблицы")
        for name, df in st.session_state.user_tables.items():
            col1, col2, col3 = st.columns([3,1,1])
            col1.write(f"**{name}** ({len(df)} команд)")
            if col2.button("Загрузить", key=f"load_{name}"):
                st.session_state.df_teams = df
                st.session_state.active_source = "user_table"
                st.session_state.selected_user_table = name
                st.rerun()
            if col3.button("🗑️", key=f"del_{name}"):
                del st.session_state.user_tables[name]
                if st.session_state.selected_user_table == name:
                    st.session_state.df_teams = None
                    st.session_state.active_source = "auto"
                st.rerun()
        with st.expander("Обновить таблицу"):
            upd_name = st.selectbox("Выберите таблицу", list(st.session_state.user_tables.keys()))
            upd_method = st.radio("Способ", ["Текстовый ввод","CSV/Excel"])
            if upd_method == "Текстовый ввод":
                upd_text = st.text_area("Новые данные", height=150)
                if st.button("Обновить"):
                    df_upd = parse_text_to_df(upd_text)
                    if df_upd is not None:
                        st.session_state.user_tables[upd_name] = df_upd
                        if st.session_state.selected_user_table == upd_name:
                            st.session_state.df_teams = df_upd
                        st.rerun()
                    else:
                        st.error("Не удалось распознать данные")
            else:
                upd_file = st.file_uploader("Файл", type=['csv','xlsx'])
                if upd_file and st.button("Обновить"):
                    try:
                        if upd_file.name.endswith('.csv'):
                            df_upd = parse_table_to_df(upd_file, 'csv')
                        else:
                            df_upd = parse_table_to_df(upd_file, 'xlsx')
                        if df_upd is not None:
                            st.session_state.user_tables[upd_name] = df_upd
                            if st.session_state.selected_user_table == upd_name:
                                st.session_state.df_teams = df_upd
                            st.rerun()
                        else:
                            st.error("Не удалось распознать файл")
                    except Exception as e:
                        st.error(str(e))
    else:
        st.info("Нет сохранённых таблиц. Создайте новую или импортируйте JSON.")

# Main area
st.subheader("Источник данных")
src = st.radio(
    "Выберите источник",
    ["Автоматический парсинг (URL)", "Ручной ввод (только одна пара)", "Загруженная таблица"],
    horizontal=True
)
if src == "Автоматический парсинг (URL)":
    st.session_state.active_source = "auto"
elif src == "Ручной ввод (только одна пара)":
    st.session_state.active_source = "manual_pair"
else:
    st.session_state.active_source = "user_table"

if st.session_state.active_source == "auto":
    with st.form("auto_form"):
        url = st.text_input("Введите URL страницы с результатами", placeholder="https://...dataproject.com/CompetitionStandings.aspx?ID=127")
        combine = False
        if "dataproject.com" in url:
            combine = st.checkbox("Складывать все этапы (только для Data Project)", value=False)
            if combine:
                st.caption("Будут автоматически найдены и просуммированы все этапы на странице.")
        load_clicked = st.form_submit_button("📥 Загрузить данные")
        if load_clicked and url:
            with st.spinner("Загрузка..."):
                df, err = load_teams_from_url(url, combine)
                if df is not None:
                    st.session_state.df_teams = df
                    detected = detect_gender_by_url(url)
                    if detected:
                        st.session_state.detected_gender = detected
                        st.success(f"Загружено {len(df)} команд. Определён пол: {detected}")
                    else:
                        st.session_state.detected_gender = "Женщины"
                        st.info("Не удалось определить пол, установлен 'Женщины' (можно изменить ниже).")
                else:
                    st.error(err)
    if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
        with st.expander("⚙️ Указать количество сыгранных матчей"):
            st.markdown("Если в данных из URL нет точного числа матчей, вы можете задать его вручную.")
            use_manual_matches = st.checkbox("Задать количество матчей вручную")
            if use_manual_matches:
                matches_value = st.number_input("Количество матчей для всех команд", min_value=1, value=30, step=1)
                if st.button("Применить ко всем командам"):
                    df = st.session_state.df_teams.copy()
                    df['Матчи'] = matches_value
                    st.session_state.df_teams = df
                    st.success(f"Для всех команд установлено количество матчей: {matches_value}")

elif st.session_state.active_source == "manual_pair":
    st.info("Введите данные для двух команд")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Домашняя**")
        home_name = st.text_input("Название", key="h_name")
        h_sv = st.number_input("Сеты выиграно", min_value=0, key="h_sv")
        h_sp = st.number_input("Сеты проиграно", min_value=0, key="h_sp")
        h_bv = st.number_input("Очки набрано", min_value=0, key="h_bv")
        h_bp = st.number_input("Очки пропущено", min_value=0, key="h_bp")
        h_m = st.number_input("Матчей", min_value=1, value=30, key="h_m")
    with col2:
        st.markdown("**Гостевая**")
        away_name = st.text_input("Название", key="a_name")
        a_sv = st.number_input("Сеты выиграно", min_value=0, key="a_sv")
        a_sp = st.number_input("Сеты проиграно", min_value=0, key="a_sp")
        a_bv = st.number_input("Очки набрано", min_value=0, key="a_bv")
        a_bp = st.number_input("Очки пропущено", min_value=0, key="a_bp")
        a_m = st.number_input("Матчей", min_value=1, value=30, key="a_m")
    if st.button("Сохранить пару"):
        if home_name and away_name:
            df = pd.DataFrame({
                'Команда': [home_name, away_name],
                'Сеты': [f"{h_sv}:{h_sp}", f"{a_sv}:{a_sp}"],
                'Мячи': [f"{h_bv}:{h_bp}", f"{a_bv}:{a_bp}"],
                'Матчи': [h_m, a_m]
            })
            st.session_state.df_teams = df
            if st.session_state.detected_gender is None:
                st.session_state.detected_gender = "Мужчины"
            st.success("Сохранено")

elif st.session_state.active_source == "user_table":
    if st.session_state.user_tables:
        selected = st.selectbox("Выберите таблицу", list(st.session_state.user_tables.keys()))
        if st.button("Активировать"):
            st.session_state.df_teams = st.session_state.user_tables[selected]
            st.session_state.selected_user_table = selected
            if st.session_state.detected_gender is None:
                st.session_state.detected_gender = "Мужчины"
            st.success(f"Активирована '{selected}'")
    else:
        st.warning("Нет таблиц. Создайте или импортируйте.")

# Прогноз
if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
    if 'Команда' not in st.session_state.df_teams.columns:
        st.error("Некорректный формат: отсутствует колонка 'Команда'")
    else:
        teams = st.session_state.df_teams['Команда'].tolist()
        st.subheader("📊 Прогноз на матч")
        gender = st.radio("Категория", ["Мужчины", "Женщины"], index=0 if st.session_state.detected_gender == "Мужчины" else 1, help="Можно изменить вручную.")
        neutral_field = st.checkbox("Нейтральное поле")
        match_format = st.radio("Формат матча", ["до 3 побед (best-of-5)", "до 2 побед (best-of-3)"], index=0)
        col1, col2 = st.columns(2)
        with col1:
            home_index = teams.index(st.session_state.home_team) if st.session_state.home_team in teams else 0
            home = st.selectbox("Домашняя", teams, index=home_index, key="home_sel")
            st.session_state.home_team = home
            home_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
            h_sets_str = home_row['Сеты']
            h_points_str = home_row['Мячи']
            h_sv, h_sp = map(int, h_sets_str.split(':'))
            h_bv, h_bp = map(int, h_points_str.split(':'))
            h_matches = home_row.get('Матчи', None)
            if pd.isna(h_matches): h_matches = None
            p_home_set = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
            st.caption(f"Сеты: {h_sv}:{h_sp} | Мячи: {h_bv}:{h_bp} | % сетов: {p_home_set:.1%}" + (f" | Матчей: {h_matches}" if h_matches else ""))
        with col2:
            away_index = teams.index(st.session_state.away_team) if st.session_state.away_team in teams else 1 if len(teams)>1 else 0
            away = st.selectbox("Гостевая", teams, index=away_index, key="away_sel")
            st.session_state.away_team = away
            away_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
            a_sets_str = away_row['Сеты']
            a_points_str = away_row['Мячи']
            a_sv, a_sp = map(int, a_sets_str.split(':'))
            a_bv, a_bp = map(int, a_points_str.split(':'))
            a_matches = away_row.get('Матчи', None)
            if pd.isna(a_matches): a_matches = None
            p_away_set = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
            st.caption(f"Сеты: {a_sv}:{a_sp} | Мячи: {a_bv}:{a_bp} | % сетов: {p_away_set:.1%}" + (f" | Матчей: {a_matches}" if a_matches else ""))

        # Личные встречи
        st.divider()
        st.subheader("📋 Личные встречи (ручной ввод)")
        all_teams = teams if len(teams) > 1 else [home, away]
        with st.expander("➕ Добавить личную встречу"):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                hh = st.selectbox("Хозяева", all_teams, key="h2h_h")
            with col_b:
                ha = st.selectbox("Гости", all_teams, key="h2h_a")
            with col_c:
                sets_h2h = st.text_input("Счёт по сетам (опционально)", placeholder="3:1")
            pts_input = st.text_input("Счёт или разница по очкам (опционально)", placeholder="75:70 или 15")
            date_h2h = st.text_input("Дата", placeholder="01.01.2026")
            if st.button("Добавить", key="add_h2h"):
                has_sets = bool(sets_h2h.strip())
                has_pts = bool(pts_input.strip())
                if not (has_sets or has_pts):
                    st.error("Укажите хотя бы один параметр: счёт по сетам или счёт/разницу по очкам")
                else:
                    error = None
                    if has_sets:
                        if ':' not in sets_h2h:
                            error = "Счёт по сетам должен содержать двоеточие, например 3:1"
                        else:
                            parts = sets_h2h.split(':')
                            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                                error = "Счёт по сетам должен состоять из двух чисел"
                    force = None
                    pts_display = None
                    if not error and has_pts:
                        if ':' in pts_input:
                            p_parts = pts_input.split(':')
                            if len(p_parts) != 2:
                                error = "Счёт по очкам должен содержать два числа, разделённых двоеточием"
                            else:
                                try:
                                    p1 = int(p_parts[0])
                                    p2 = int(p_parts[1])
                                    force = p1 - p2
                                    pts_display = pts_input
                                except:
                                    error = "Счёт по очкам должен содержать целые числа"
                        else:
                            try:
                                force = float(pts_input)
                                pts_display = pts_input
                            except:
                                error = "Разница по очкам должна быть числом"
                    if error:
                        st.error(error)
                    else:
                        key = (hh, ha)
                        st.session_state.h2h_manual.setdefault(key, []).append({
                            'Дата': date_h2h or "(нет даты)",
                            'Хозяева': hh,
                            'Гости': ha,
                            'Счёт по сетам': sets_h2h if has_sets else None,
                            'Счёт по очкам': pts_display,
                            'Фора по очкам': force
                        })
                        st.success("Добавлено")
                        st.rerun()

        # Приводим встречи к паре (home, away)
        key_pair = (home, away)
        rev_key = (away, home)
        current_h2h = []
        for m in st.session_state.h2h_manual.get(key_pair, []):
            current_h2h.append(m)
        for m in st.session_state.h2h_manual.get(rev_key, []):
            m2 = m.copy()
            m2['Хозяева'] = home
            m2['Гости'] = away
            if m['Счёт по сетам']:
                parts = m['Счёт по сетам'].split(':')
                m2['Счёт по сетам'] = f"{parts[1]}:{parts[0]}"
            if m['Счёт по очкам']:
                if m['Фора по очкам'] is not None:
                    m2['Фора по очкам'] = -m['Фора по очкам']
                    if m['Счёт по очкам'].replace('-', '').isdigit():
                        m2['Счёт по очкам'] = str(-float(m['Счёт по очкам']))
                    elif ':' in m['Счёт по очкам']:
                        pts_parts = m['Счёт по очкам'].split(':')
                        m2['Счёт по очкам'] = f"{pts_parts[1]}:{pts_parts[0]}"
            current_h2h.append(m2)

        if current_h2h:
            st.subheader(f"История встреч: {home} – {away}")
            display_data = []
            for m in current_h2h:
                display_data.append({
                    'Дата': m['Дата'],
                    'Хозяева': m['Хозяева'],
                    'Гости': m['Гости'],
                    'Счёт по сетам': m['Счёт по сетам'] if m['Счёт по сетам'] else '—',
                    'Счёт по очкам': m['Счёт по очкам'] if m['Счёт по очкам'] else '—',
                    'Фора (хозяева)': m['Фора по очкам'] if m['Фора по очкам'] is not None else '—'
                })
            st.dataframe(pd.DataFrame(display_data))
            if st.button("Очистить историю этой пары"):
                st.session_state.h2h_manual.pop(key_pair, None)
                st.session_state.h2h_manual.pop(rev_key, None)
                st.rerun()
        else:
            st.info("Нет данных о личных встречах. Добавьте вручную.")

        # Расчёт прогноза
        use_h2h = st.checkbox("Учитывать личные встречи (включено – усреднение с полной статистикой, выключено – вычитание из статистики и затем усреднение)", value=True)

        if st.button("Рассчитать котировки", key="calc"):
            if home == away:
                st.error("Выберите разные команды")
            else:
                # Полные данные
                h_sv_full, h_sp_full = h_sv, h_sp
                h_bv_full, h_bp_full = h_bv, h_bp
                h_matches_full = h_matches
                a_sv_full, a_sp_full = a_sv, a_sp
                a_bv_full, a_bp_full = a_bv, a_bp
                a_matches_full = a_matches

                # Полная фора
                full_raw = None
                if h_matches_full is not None and a_matches_full is not None and h_matches_full > 0 and a_matches_full > 0:
                    full_raw = calculate_raw_handicap(
                        h_sv_full, h_sp_full, h_bv_full, h_bp_full, h_matches_full,
                        a_sv_full, a_sp_full, a_bv_full, a_bp_full, a_matches_full
                    )

                # Очищенная статистика (без личных встреч)
                h_sv_clean, h_sp_clean = h_sv_full, h_sp_full
                h_bv_clean, h_bp_clean = h_bv_full, h_bp_full
                h_matches_clean = h_matches_full
                a_sv_clean, a_sp_clean = a_sv_full, a_sp_full
                a_bv_clean, a_bp_clean = a_bv_full, a_bp_full
                a_matches_clean = a_matches_full
                n_h2h_full = 0
                if current_h2h:
                    h_sets_w_sub = 0
                    h_sets_l_sub = 0
                    h_pts_w_sub = 0
                    h_pts_l_sub = 0
                    a_sets_w_sub = 0
                    a_sets_l_sub = 0
                    a_pts_w_sub = 0
                    a_pts_l_sub = 0
                    for match in current_h2h:
                        if match['Счёт по сетам'] and match['Счёт по очкам'] and ':' in str(match['Счёт по очкам']):
                            sets_parts = match['Счёт по сетам'].split(':')
                            h_sets_w_sub += int(sets_parts[0])
                            h_sets_l_sub += int(sets_parts[1])
                            pts_parts = match['Счёт по очкам'].split(':')
                            h_pts_w_sub += int(pts_parts[0])
                            h_pts_l_sub += int(pts_parts[1])
                            a_sets_w_sub += int(sets_parts[1])
                            a_sets_l_sub += int(sets_parts[0])
                            a_pts_w_sub += int(pts_parts[1])
                            a_pts_l_sub += int(pts_parts[0])
                            n_h2h_full += 1
                    if n_h2h_full > 0:
                        h_sv_clean = h_sv_full - h_sets_w_sub
                        h_sp_clean = h_sp_full - h_sets_l_sub
                        h_bv_clean = h_bv_full - h_pts_w_sub
                        h_bp_clean = h_bp_full - h_pts_l_sub
                        h_matches_clean = h_matches_full - n_h2h_full if h_matches_full is not None else None
                        a_sv_clean = a_sv_full - a_sets_w_sub
                        a_sp_clean = a_sp_full - a_sets_l_sub
                        a_bv_clean = a_bv_full - a_pts_w_sub
                        a_bp_clean = a_bp_full - a_pts_l_sub
                        a_matches_clean = a_matches_full - n_h2h_full if a_matches_full is not None else None
                        if (h_sv_clean < 0 or h_sp_clean < 0 or h_bv_clean < 0 or h_bp_clean < 0 or
                            a_sv_clean < 0 or a_sp_clean < 0 or a_bv_clean < 0 or a_bp_clean < 0 or
                            (h_matches_clean is not None and h_matches_clean < 0) or
                            (a_matches_clean is not None and a_matches_clean < 0)):
                            st.warning("Некорректное вычитание: личные встречи, вероятно, уже учтены. Использую полную статистику.")
                            h_sv_clean, h_sp_clean = h_sv_full, h_sp_full
                            h_bv_clean, h_bp_clean = h_bv_full, h_bp_full
                            h_matches_clean = h_matches_full
                            a_sv_clean, a_sp_clean = a_sv_full, a_sp_full
                            a_bv_clean, a_bp_clean = a_bv_full, a_bp_full
                            a_matches_clean = a_matches_full
                            n_h2h_full = 0
                clean_raw = None
                if h_matches_clean is not None and a_matches_clean is not None and h_matches_clean > 0 and a_matches_clean > 0:
                    clean_raw = calculate_raw_handicap(
                        h_sv_clean, h_sp_clean, h_bv_clean, h_bp_clean, h_matches_clean,
                        a_sv_clean, a_sp_clean, a_bv_clean, a_bp_clean, a_matches_clean
                    )

                # Средняя фора из личных встреч
                h2h_forces = [m['Фора по очкам'] for m in current_h2h if m['Фора по очкам'] is not None]
                avg_h2h = sum(h2h_forces) / len(h2h_forces) if h2h_forces else None

                if use_h2h:
                    if full_raw is not None and avg_h2h is not None:
                        final_raw = (full_raw + avg_h2h) / 2
                        st.caption(f"Полная фора (включая личные встречи): {full_raw:.1f}, средняя фора из личных встреч: {avg_h2h:.1f} → усреднённая: {final_raw:.1f}")
                    elif full_raw is not None:
                        final_raw = full_raw
                        st.caption(f"Личные встречи без форы, используется полная фора: {final_raw:.1f}")
                    elif avg_h2h is not None:
                        final_raw = avg_h2h
                        st.caption(f"Нет данных по общей статистике, используется средняя фора личных встреч: {final_raw:.1f}")
                    else:
                        final_raw = None
                        st.error("Нет данных для расчёта форы")
                else:
                    if clean_raw is not None and avg_h2h is not None:
                        final_raw = (clean_raw + avg_h2h) / 2
                        st.caption(f"Фора без учёта личных встреч: {clean_raw:.1f}, средняя фора из личных встреч: {avg_h2h:.1f} → усреднённая: {final_raw:.1f}")
                    elif clean_raw is not None:
                        final_raw = clean_raw
                        st.caption(f"Личные встречи без форы, используется фора без учёта личных встреч: {final_raw:.1f}")
                    elif avg_h2h is not None:
                        final_raw = avg_h2h
                        st.caption(f"Нет данных по статистике без личек, используется средняя фора личных встреч: {final_raw:.1f}")
                    else:
                        final_raw = None
                        st.error("Нет данных для расчёта форы")

                # Прогноз по сетам (на основе полных данных)
                p_home = h_sv_full / (h_sv_full + h_sp_full) if (h_sv_full + h_sp_full) > 0 else 0.5
                p_away = a_sv_full / (a_sv_full + a_sp_full) if (a_sv_full + a_sp_full) > 0 else 0.5
                best_of = 3 if match_format.startswith("до 2") else 5
                prob_home_match = prob_win_match(p_home, best_of)
                prob_away_match = prob_win_match(p_away, best_of)
                total = prob_home_match + prob_away_match
                prob_home_norm = prob_home_match / total
                prob_away_norm = prob_away_match / total
                favorite = home if prob_home_norm > prob_away_norm else away
                fav_prob = max(prob_home_norm, prob_away_norm)
                margin = 0.05
                odds = (1 - margin) / fav_prob
                st.subheader("📈 Прогноз по сетам")
                st.write(f"**Победа {favorite} – коэффициент {odds:.2f}**")
                st.caption(f"Вероятность победы в матче через биномиальное распределение (best-of-{best_of}), нормализована.")

                # Прогноз по очкам (скорректированный)
                if final_raw is not None:
                    min_matches = min(h_matches_full if h_matches_full else 999, a_matches_full if a_matches_full else 999)
                    if gender == "Мужчины":
                        if min_matches == 2:
                            adjusted = adjust_handicap_men_2(final_raw)
                            formula = "мужской (2 игры)"
                        elif min_matches == 3:
                            adjusted = adjust_handicap_men_3(final_raw)
                            formula = "мужской (3 игры)"
                        else:
                            if neutral_field:
                                adjusted = adjust_handicap_men_neutral(final_raw)
                                formula = "мужской нейтральной (4+ матчей)"
                            else:
                                adjusted = adjust_handicap_men_home(final_raw)
                                formula = "мужской домашней (4+ матчей)"
                    else:
                        if min_matches == 2:
                            adjusted = adjust_handicap_women_2(final_raw)
                            formula = "женской (2 игры)"
                        elif min_matches == 3:
                            adjusted = adjust_handicap_women_3(final_raw)
                            formula = "женской (3 игры)"
                        else:
                            if neutral_field:
                                adjusted = adjust_handicap_women_neutral(final_raw)
                                formula = "женской нейтральной (4+ матчей)"
                            else:
                                adjusted = adjust_handicap_women_home(final_raw)
                                formula = "женской домашней (4+ матчей)"
                    st.subheader("⚖️ Прогноз по очкам (скорректированный)")
                    if adjusted > 0:
                        st.success(f"Фора на матч: {adjusted:.1f} (в пользу хозяев)")
                    elif adjusted < 0:
                        st.success(f"Фора на матч: {adjusted:.1f} (в пользу гостей)")
                    else:
                        st.info("Фора близка к нулю")
                    st.caption(f"Исходная фора (сырая): {final_raw:.1f} → скорректировано по {formula}")
                else:
                    st.info("Не удалось рассчитать фору по очкам. Убедитесь, что указано количество матчей и есть данные.")
else:
    st.info("Выберите источник данных и загрузите команды.")
