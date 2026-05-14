import streamlit as st
import pandas as pd
import re
import math
import json
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# ==================== КОРРЕКТИРОВКИ ФОРЫ (без изменений) ====================
def adjust_handicap_men_home(handicap: float) -> float:
    if handicap <= -43:
        return handicap * 1.3
    elif handicap <= -34.5:
        return handicap * 1.38
    elif handicap <= -17.5:
        return handicap * 1.48
    elif handicap <= -12.5:
        return handicap * 1.7
    elif handicap <= -9.5:
        return handicap * 1.9
    elif handicap <= -7.5:
        return handicap * 2.0
    elif handicap <= -6.5:
        return handicap * 2.2
    elif handicap <= -5.5:
        return handicap * 1.94
    elif handicap <= -4.5:
        return handicap * 1.9
    elif handicap <= -3.5:
        return handicap * 1.8
    elif handicap <= -2.75:
        return handicap * 2.1
    elif handicap <= -2.25:
        return handicap * 1.75
    elif handicap <= -1.75:
        return handicap * 1.0
    elif handicap <= -1.25:
        return handicap * 0.5
    elif handicap <= -0.75:
        return handicap * 0.0
    elif handicap < 1.25:
        return handicap + 2.5
    elif handicap < 1.75:
        return handicap * 3.5
    elif handicap < 2.75:
        return handicap * 3.7
    elif handicap < 3.5:
        return handicap * 3.6
    elif handicap < 4.5:
        return handicap * 3.2
    elif handicap < 6.5:
        return handicap * 2.7
    elif handicap < 7.5:
        return handicap * 2.5
    elif handicap < 9.5:
        return handicap * 2.4
    elif handicap < 10.5:
        return handicap * 2.3
    elif handicap < 14.5:
        return handicap * 2.2
    elif handicap < 17.5:
        return handicap * 2.0
    elif handicap < 21.5:
        return handicap * 1.68
    elif handicap < 34.5:
        return handicap * 1.65
    elif handicap < 43:
        return handicap * 1.38
    else:
        return handicap * 1.3

def adjust_handicap_men_neutral(handicap: float) -> float:
    if handicap <= -43:
        return handicap * 1.3
    elif handicap <= -34.5:
        return handicap * 1.38
    elif handicap <= -21.5:
        return handicap * 1.57
    elif handicap <= -17.5:
        return handicap * 1.58
    elif handicap <= -14.5:
        return handicap * 1.85
    elif handicap <= -12.5:
        return handicap * 1.95
    elif handicap <= -10.5:
        return handicap * 2.05
    elif handicap <= -9.5:
        return handicap * 2.1
    elif handicap <= -7.5:
        return handicap * 2.2
    elif handicap <= -4.5:
        return handicap * 2.3
    elif handicap <= -3.5:
        return handicap * 2.5
    elif handicap <= -2.75:
        return handicap * 2.85
    elif handicap <= -2.25:
        return handicap * 2.73
    elif handicap <= -1.85:
        return handicap * 2.35
    elif handicap <= -1.65:
        return handicap * 1.8
    elif handicap <= -1.25:
        return handicap * 1.48
    elif handicap < 1.25:
        return handicap * 1.0
    elif handicap < 1.6:
        return handicap * 1.48
    elif handicap < 1.85:
        return handicap * 1.8
    elif handicap < 2.25:
        return handicap * 2.35
    elif handicap < 2.75:
        return handicap * 2.73
    elif handicap < 3.5:
        return handicap * 2.85
    elif handicap < 4.5:
        return handicap * 2.5
    elif handicap < 7.5:
        return handicap * 2.3
    elif handicap < 9.5:
        return handicap * 2.2
    elif handicap < 10.5:
        return handicap * 2.1
    elif handicap < 12.5:
        return handicap * 2.05
    elif handicap < 14.5:
        return handicap * 1.95
    elif handicap < 17.5:
        return handicap * 1.85
    elif handicap < 21.5:
        return handicap * 1.58
    elif handicap < 34.5:
        return handicap * 1.57
    elif handicap < 43:
        return handicap * 1.38
    else:
        return handicap * 1.3

def adjust_handicap_women_home(handicap: float) -> float:
    if handicap <= -43:
        return handicap * 1.3
    elif handicap <= -38.5:
        return handicap * 1.38
    elif handicap <= -27.5:
        return handicap * 1.5
    elif handicap <= -25.5:
        return handicap * 1.54
    elif handicap <= -17.5:
        return handicap * 1.58
    elif handicap <= -16.5:
        return handicap * 1.75
    elif handicap <= -14.5:
        return handicap * 1.8
    elif handicap <= -10.5:
        return handicap * 2.0
    elif handicap <= -4.5:
        return handicap * 2.2
    elif handicap <= -3.75:
        return handicap * 2.1
    elif handicap <= -3.25:
        return handicap * 1.75
    elif handicap <= -2.75:
        return handicap * 1.5
    elif handicap <= -2.25:
        return handicap * 1.0
    elif handicap <= -1.75:
        return handicap * 0.5
    elif handicap <= -1.5:
        return handicap * 0.0
    elif handicap <= -1.25:
        return handicap * -0.6
    elif handicap <= -0.75:
        return handicap * -3
    elif handicap < 0:
        return handicap + 3.5
    elif handicap == 0:
        return 3.5
    elif handicap < 0.75:
        return handicap + 3.5
    elif handicap < 1.25:
        return handicap + 3.5
    elif handicap < 1.75:
        return handicap * 3.5
    elif handicap < 2.25:
        return handicap * 4.0
    elif handicap < 2.75:
        return handicap * 4.8
    elif handicap < 3.5:
        return handicap * 4.0
    elif handicap < 4.5:
        return handicap * 3.3
    elif handicap < 5.5:
        return handicap * 2.5
    elif handicap < 6.5:
        return handicap * 2.5
    elif handicap < 7.5:
        return handicap * 2.5
    elif handicap < 10.5:
        return handicap * 2.4
    elif handicap < 11.5:
        return handicap * 2.3
    elif handicap < 12.5:
        return handicap * 2.1
    elif handicap < 14.5:
        return handicap * 1.9
    elif handicap < 23.5:
        return handicap * 1.8
    elif handicap < 29.5:
        return handicap * 1.62
    elif handicap < 38.5:
        return handicap * 1.5
    elif handicap < 43:
        return handicap * 1.38
    else:
        return handicap * 1.3

def adjust_handicap_women_neutral(handicap: float) -> float:
    if handicap <= -43:
        return handicap * 1.3
    elif handicap <= -38.5:
        return handicap * 1.38
    elif handicap <= -29.5:
        return handicap * 1.5
    elif handicap <= -27.5:
        return handicap * 1.56
    elif handicap <= -25.5:
        return handicap * 1.58
    elif handicap <= -23.5:
        return handicap * 1.6
    elif handicap <= -17.5:
        return handicap * 1.69
    elif handicap <= -14.5:
        return handicap * 1.8
    elif handicap <= -12.5:
        return handicap * 1.95
    elif handicap <= -11.5:
        return handicap * 2.05
    elif handicap <= -10.5:
        return handicap * 2.15
    elif handicap <= -6.5:
        return handicap * 2.3
    elif handicap <= -5.5:
        return handicap * 2.4
    elif handicap <= -4.5:
        return handicap * 2.5
    elif handicap <= -3.5:
        return handicap * 2.8
    elif handicap <= -2.25:
        return handicap * 2.9
    elif handicap <= -1.85:
        return handicap * 2.25
    elif handicap <= -1.65:
        return handicap * 1.8
    elif handicap <= -1.25:
        return handicap * 1.48
    elif handicap < 1.25:
        return handicap * 1.0
    elif handicap < 1.6:
        return handicap * 1.48
    elif handicap < 1.85:
        return handicap * 1.8
    elif handicap < 2.25:
        return handicap * 2.25
    elif handicap < 3.5:
        return handicap * 2.9
    elif handicap < 4.5:
        return handicap * 2.8
    elif handicap < 5.5:
        return handicap * 2.5
    elif handicap < 6.5:
        return handicap * 2.4
    elif handicap < 10.5:
        return handicap * 2.3
    elif handicap < 11.5:
        return handicap * 2.15
    elif handicap < 12.5:
        return handicap * 2.05
    elif handicap < 14.5:
        return handicap * 1.95
    elif handicap < 17.5:
        return handicap * 1.8
    elif handicap < 23.5:
        return handicap * 1.69
    elif handicap < 25.5:
        return handicap * 1.6
    elif handicap < 27.5:
        return handicap * 1.58
    elif handicap < 29.5:
        return handicap * 1.56
    elif handicap < 38.5:
        return handicap * 1.5
    elif handicap < 43:
        return handicap * 1.38
    else:
        return handicap * 1.3

def adjust_handicap_men_2matches(handicap: float) -> float:
    if handicap <= -33.5:
        return handicap * 1.33
    elif handicap <= -19.5:
        return handicap * 1.42
    elif handicap <= -14.5:
        return handicap * 1.25
    elif handicap <= -12.5:
        return handicap * 1.5
    elif handicap <= -10.5:
        return handicap * 1.68
    elif handicap <= -9.5:
        return handicap * 1.45
    elif handicap <= -8.5:
        return handicap * 1.4
    elif handicap <= -6.5:
        return handicap * 1.56
    elif handicap <= -5.5:
        return handicap * 1.6
    elif handicap <= -4.5:
        return handicap * 2.1
    elif handicap <= -3.5:
        return handicap * 2.4
    elif handicap <= -2.75:
        return handicap * 2.5
    elif handicap <= -2.25:
        return handicap * 1.9
    elif handicap <= -1.5:
        return handicap * 1.44
    elif handicap <= -0.5:
        return handicap * 2.0
    elif handicap < 0:
        return handicap - 0.75
    elif handicap == 0:
        return 0.0
    elif handicap < 0.5:
        return handicap + 0.75
    elif handicap < 1.5:
        return handicap * 2.0
    elif handicap < 2.25:
        return handicap * 1.44
    elif handicap < 2.75:
        return handicap * 1.9
    elif handicap < 3.5:
        return handicap * 2.5
    elif handicap < 4.5:
        return handicap * 2.4
    elif handicap < 5.5:
        return handicap * 2.1
    elif handicap < 6.5:
        return handicap * 1.6
    elif handicap < 8.5:
        return handicap * 1.56
    elif handicap < 9.5:
        return handicap * 1.4
    elif handicap < 10.5:
        return handicap * 1.45
    elif handicap < 12.5:
        return handicap * 1.68
    elif handicap < 14.5:
        return handicap * 1.5
    elif handicap < 19.5:
        return handicap * 1.25
    elif handicap < 33.5:
        return handicap * 1.42
    else:
        return handicap * 1.33

def adjust_handicap_women_2matches(handicap: float) -> float:
    if handicap <= -26.5:
        return handicap * 1.33
    elif handicap <= -19.5:
        return handicap * 1.42
    elif handicap <= -17.5:
        return handicap * 1.65
    elif handicap <= -14.5:
        return handicap * 1.4
    elif handicap <= -13.5:
        return handicap * 1.5
    elif handicap <= -12.5:
        return handicap * 1.7
    elif handicap <= -11.5:
        return handicap * 1.73
    elif handicap <= -9.5:
        return handicap * 1.9
    elif handicap <= -8.5:
        return handicap * 1.83
    elif handicap <= -5.5:
        return handicap * 1.83
    elif handicap <= -4.5:
        return handicap * 1.87
    elif handicap <= -3.5:
        return handicap * 2.8
    elif handicap <= -2.5:
        return handicap * 3.0
    elif handicap <= -1.75:
        return handicap * 4.2
    elif handicap < -1.25:
        return handicap * 3.75
    elif handicap < 0:
        return handicap - 0.0
    elif handicap == 0:
        return 0.0
    elif handicap <= 1.25:
        return handicap + 0.0
    elif handicap < 1.75:
        return handicap * 3.75
    elif handicap <= 2.5:
        return handicap * 4.2
    elif handicap < 3.5:
        return handicap * 3.0
    elif handicap < 4.5:
        return handicap * 2.8
    elif handicap < 5.5:
        return handicap * 1.87
    elif handicap < 8.5:
        return handicap * 1.83
    elif handicap < 9.5:
        return handicap * 1.83
    elif handicap < 11.5:
        return handicap * 1.9
    elif handicap < 12.5:
        return handicap * 1.73
    elif handicap < 13.5:
        return handicap * 1.7
    elif handicap < 14.5:
        return handicap * 1.5
    elif handicap < 17.5:
        return handicap * 1.4
    elif handicap < 19.5:
        return handicap * 1.65
    elif handicap < 26.5:
        return handicap * 1.42
    else:
        return handicap * 1.33

def adjust_handicap_men_3matches(handicap: float) -> float:
    if handicap <= -20.5:
        return handicap * 1.3
    elif handicap <= -18.5:
        return handicap * 1.6
    elif handicap <= -9.5:
        return handicap * 1.7
    elif handicap <= -7.5:
        return handicap * 1.5
    elif handicap <= -6.5:
        return handicap * 2.0
    elif handicap <= -5.5:
        return handicap * 2.55
    elif handicap <= -4.5:
        return handicap * 2.4
    elif handicap <= -3.75:
        return handicap * 2.2
    elif handicap <= -3.25:
        return handicap * 1.85
    elif handicap <= -1.5:
        return handicap * 1.5
    elif handicap < 0:
        return handicap - 5.0
    elif handicap == 0:
        return 0.0
    elif handicap < 1.5:
        return handicap + 5.0
    elif handicap < 3.25:
        return handicap * 1.5
    elif handicap <= 3.75:
        return handicap * 1.85
    elif handicap < 4.5:
        return handicap * 2.2
    elif handicap < 5.5:
        return handicap * 2.4
    elif handicap < 6.5:
        return handicap * 2.55
    elif handicap < 7.5:
        return handicap * 2.0
    elif handicap < 9.5:
        return handicap * 1.5
    elif handicap < 18.5:
        return handicap * 1.7
    elif handicap < 20.5:
        return handicap * 1.6
    else:
        return handicap * 1.3

def adjust_handicap_women_3matches(handicap: float) -> float:
    if handicap <= -28.5:
        return handicap * 1.4
    elif handicap <= -14.5:
        return handicap * 1.55
    elif handicap <= -13.5:
        return handicap * 1.65
    elif handicap <= -12.5:
        return handicap * 1.75
    elif handicap <= -11.5:
        return handicap * 1.85
    elif handicap <= -10.5:
        return handicap * 2.1
    elif handicap <= -9.5:
        return handicap * 2.6
    elif handicap <= -8.5:
        return handicap * 2.6
    elif handicap <= -7.5:
        return handicap * 1.42
    elif handicap <= -6.5:
        return handicap * 1.42
    elif handicap <= -5.5:
        return handicap * 1.42
    elif handicap <= -4.5:
        return handicap * 1.42
    elif handicap <= -3.5:
        return handicap * 1.6
    elif handicap <= -2.75:
        return handicap * 0.63
    elif handicap <= -2.25:
        return handicap - 2.5
    elif handicap < 0:
        return handicap - 5.0
    elif handicap == 0:
        return 0.0
    elif handicap < 2.25:
        return handicap + 5.0
    elif handicap < 2.75:
        return handicap + 2.5
    elif handicap <= 3.5:
        return handicap * 1.63
    elif handicap < 4.5:
        return handicap * 1.6
    elif handicap < 5.5:
        return handicap * 1.42
    elif handicap < 6.5:
        return handicap * 1.42
    elif handicap < 7.5:
        return handicap * 1.42
    elif handicap < 8.5:
        return handicap * 1.42
    elif handicap < 9.5:
        return handicap * 2.6
    elif handicap < 10.5:
        return handicap * 2.6
    elif handicap < 11.5:
        return handicap * 2.1
    elif handicap < 12.5:
        return handicap * 1.85
    elif handicap < 13.5:
        return handicap * 1.75
    elif handicap < 14.5:
        return handicap * 1.65
    elif handicap < 28.5:
        return handicap * 1.55
    else:
        return handicap * 1.4

# ==================== ПАРСЕРЫ ТАБЛИЦ (без изменений) ====================
def parse_table_to_df(data_source, file_type=None):
    # ... (полный код как в предыдущем сообщении, для краткости опущен, но в итоговом файле он есть)
    # В реальности скопируйте сюда полную функцию из предыдущего ответа.
    pass

def parse_text_to_df(text: str) -> pd.DataFrame:
    # ... (аналогично)
    pass

# ==================== ОБЩИЕ ФУНКЦИИ ====================
def prob_win_match(p: float) -> float:
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    q = 1 - p
    return 10 * p**3 * q**2 + 5 * p**4 * q + p**5

def compute_raw_handicap_without_h2h(h_data, a_data):
    h_matches = h_data['matches'] if h_data['matches'] is not None else (h_data['sets_w'] + h_data['sets_l']) // 3
    a_matches = a_data['matches'] if a_data['matches'] is not None else (a_data['sets_w'] + a_data['sets_l']) // 3
    if h_matches is None or h_matches <= 0:
        h_matches = (h_data['sets_w'] + h_data['sets_l']) // 3 if (h_data['sets_w'] + h_data['sets_l']) > 0 else 1
    if a_matches is None or a_matches <= 0:
        a_matches = (a_data['sets_w'] + a_data['sets_l']) // 3 if (a_data['sets_w'] + a_data['sets_l']) > 0 else 1
    avg_h = (h_data['pts_w'] - h_data['pts_l']) / h_matches
    avg_a = (a_data['pts_w'] - a_data['pts_l']) / a_matches
    return avg_h - avg_a, h_matches, a_matches

def compute_raw_handicap_with_h2h(h_data, a_data, h2h_encounters):
    h_pts_diff_orig = h_data['pts_w'] - h_data['pts_l']
    a_pts_diff_orig = a_data['pts_w'] - a_data['pts_l']
    h_matches_orig = h_data['matches'] if h_data['matches'] is not None else None
    a_matches_orig = a_data['matches'] if a_data['matches'] is not None else None
    if h_matches_orig is None or h_matches_orig <= 0:
        h_matches_orig = (h_data['sets_w'] + h_data['sets_l']) // 3 if (h_data['sets_w'] + h_data['sets_l']) > 0 else 1
    if a_matches_orig is None or a_matches_orig <= 0:
        a_matches_orig = (a_data['sets_w'] + a_data['sets_l']) // 3 if (a_data['sets_w'] + a_data['sets_l']) > 0 else 1

    sum_h_diff = 0
    count = 0
    for enc in h2h_encounters:
        if enc['home'] == h_data['name']:
            sum_h_diff += enc['pts_diff']
        else:
            sum_h_diff += -enc['pts_diff']
        count += 1

    h_pts_diff_adj = h_pts_diff_orig - sum_h_diff
    h_matches_adj = h_matches_orig - count
    if h_matches_adj <= 0:
        h_matches_adj = 1
    a_pts_diff_adj = a_pts_diff_orig + sum_h_diff
    a_matches_adj = a_matches_orig - count
    if a_matches_adj <= 0:
        a_matches_adj = 1

    avg_h = h_pts_diff_adj / h_matches_adj
    avg_a = a_pts_diff_adj / a_matches_adj
    return avg_h - avg_a, h_matches_adj, a_matches_adj

def detect_gender_by_url(url: str) -> str:
    url_lower = url.lower()
    if any(x in url_lower for x in ['femminile', 'women', 'kadinlar', 'liga kobiet', 'womens', 'legavolleyfemminile']):
        return "Женщины"
    if any(x in url_lower for x in ['superlega', 'plusliga', 'legavolley.it', 'volley.ru']):
        return "Мужчины"
    return None

# ==================== ПАРСЕРЫ URL ====================
def get_parser_by_url(url: str):
    if "volley.ru" in url:
        return RussiaVolleyRuParser()
    elif "dataproject.com" in url:
        return DataProjectParser()
    else:
        return None

def load_teams_from_url(url, combine_phases):
    parser = get_parser_by_url(url)
    if parser is None:
        return None, "URL не поддерживается"
    df, error = parser.fetch_stats(url, combine_phases=combine_phases)
    if df is not None and not df.empty and 'Команда' in df.columns:
        return df, None
    return None, error or "Не удалось загрузить данные"

# ==================== ИНИЦИАЛИЗАЦИЯ STREAMLIT ====================
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

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
# Для сохранения выбранных команд
if 'home_team' not in st.session_state:
    st.session_state.home_team = None
if 'away_team' not in st.session_state:
    st.session_state.away_team = None

# ==================== БОКОВАЯ ПАНЕЛЬ (ТАБЛИЦЫ) ====================
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
                st.rerun()
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

# ==================== ОСНОВНАЯ ОБЛАСТЬ ====================
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

# -------------------- 1. АВТОМАТИЧЕСКИЙ ПАРСИНГ --------------------
if st.session_state.active_source == "auto":
    with st.form("auto_form"):
        url = st.text_input("URL", placeholder="https://volley.ru/... или dataproject.com...")
        combine = False
        if "dataproject.com" in url:
            combine = st.checkbox("Складывать все этапы")
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
                        st.session_state.detected_gender = "Мужчины"
                        st.info("Не удалось определить пол, установлен 'Мужчины' (можно изменить ниже).")
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

# -------------------- 2. РУЧНОЙ ВВОД ПАРЫ --------------------
elif st.session_state.active_source == "manual_pair":
    st.info("Введите данные для двух команд")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Домашняя**")
        home_name = st.text_input("Название", key="h_name")
        h_sv = st.number_input("Sets V", min_value=0, key="h_sv")
        h_sp = st.number_input("Sets P", min_value=0, key="h_sp")
        h_bv = st.number_input("Balls V", min_value=0, key="h_bv")
        h_bp = st.number_input("Balls P", min_value=0, key="h_bp")
        h_m = st.number_input("Матчей", min_value=1, value=30, key="h_m")
    with col2:
        st.markdown("**Гостевая**")
        away_name = st.text_input("Название", key="a_name")
        a_sv = st.number_input("Sets V", min_value=0, key="a_sv")
        a_sp = st.number_input("Sets P", min_value=0, key="a_sp")
        a_bv = st.number_input("Balls V", min_value=0, key="a_bv")
        a_bp = st.number_input("Balls P", min_value=0, key="a_bp")
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

# -------------------- 3. ЗАГРУЖЕННАЯ ТАБЛИЦА --------------------
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

# ==================== ПРОГНОЗ ====================
if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
    if 'Команда' not in st.session_state.df_teams.columns:
        st.error("Некорректный формат: отсутствует колонка 'Команда'")
    else:
        teams = st.session_state.df_teams['Команда'].tolist()
        st.subheader("📊 Прогноз на матч")
        
        gender = st.radio(
            "Категория (для корректировки форы)",
            ["Мужчины", "Женщины"],
            index=0 if st.session_state.detected_gender == "Мужчины" else 1,
            help="Автоматически определено по URL, но вы можете изменить вручную."
        )
        neutral_field = st.checkbox("Нейтральное поле", help="При нейтральном поле корректировка форы происходит по отдельным формулам")
        subtract_h2h = st.checkbox("Вычитать личные встречи из статистики", value=False, help="Если включено, то разницы в очках из личных встреч будут вычтены из общей статистики команд")
        
        col1, col2 = st.columns(2)
        with col1:
            home_index = teams.index(st.session_state.home_team) if st.session_state.home_team in teams else 0
            home = st.selectbox("Домашняя", teams, index=home_index, key="home_sel")
            st.session_state.home_team = home
            home_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
            h_sv, h_sp = map(int, home_row['Сеты'].split(':'))
            h_bv, h_bp = map(int, home_row['Мячи'].split(':'))
            h_matches = home_row['Матчи'] if 'Матчи' in home_row and pd.notna(home_row['Матчи']) else None
            p_home_set = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
            st.caption(f"Сеты: {h_sv}:{h_sp} | Мячи: {h_bv}:{h_bp} | % сетов: {p_home_set:.1%}")
            if h_matches:
                st.caption(f"Матчей: {h_matches}")
        with col2:
            away_index = teams.index(st.session_state.away_team) if st.session_state.away_team in teams else 1 if len(teams)>1 else 0
            away = st.selectbox("Гостевая", teams, index=away_index, key="away_sel")
            st.session_state.away_team = away
            away_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
            a_sv, a_sp = map(int, away_row['Сеты'].split(':'))
            a_bv, a_bp = map(int, away_row['Мячи'].split(':'))
            a_matches = away_row['Матчи'] if 'Матчи' in away_row and pd.notna(away_row['Матчи']) else None
            p_away_set = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
            st.caption(f"Сеты: {a_sv}:{a_sp} | Мячи: {a_bv}:{a_bp} | % сетов: {p_away_set:.1%}")
            if a_matches:
                st.caption(f"Матчей: {a_matches}")

        # Сбор личных встреч между home и away
        key_pair = (home, away)
        rev_key = (away, home)
        h2h_encounters = []
        for m in st.session_state.h2h_manual.get(key_pair, []):
            h2h_encounters.append({
                'home': m['Хозяева'],
                'away': m['Гости'],
                'pts_diff': m['Фора по очкам']
            })
        for m in st.session_state.h2h_manual.get(rev_key, []):
            h2h_encounters.append({
                'home': m['Хозяева'],
                'away': m['Гости'],
                'pts_diff': m['Фора по очкам']
            })

        # Форма для добавления личной встречи (без rerun при изменении полей)
        with st.expander("➕ Добавить личную встречу"):
            with st.form(key="add_h2h_form"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    hh = st.selectbox("Хозяева", teams, key="h2h_h")
                with col_b:
                    ha = st.selectbox("Гости", teams, key="h2h_a")
                with col_c:
                    sets_h2h = st.text_input("Счёт по сетам", placeholder="3:1")
                pts_h2h = st.number_input("Фора по очкам (+, если хозяева выиграли)", step=0.5, key="pts_h2h")
                date_h2h = st.text_input("Дата", placeholder="01.01.2026")
                submitted = st.form_submit_button("Добавить")
                if submitted:
                    key = (hh, ha)
                    st.session_state.h2h_manual.setdefault(key, []).append({
                        'Дата': date_h2h or "(нет даты)",
                        'Хозяева': hh,
                        'Гости': ha,
                        'Счёт по сетам': sets_h2h,
                        'Фора по очкам': pts_h2h
                    })
                    st.success("Добавлено")
                    st.rerun()

        # Отображение текущей истории встреч
        current_h2h = []
        for m in st.session_state.h2h_manual.get(key_pair, []):
            current_h2h.append(m)
        for m in st.session_state.h2h_manual.get(rev_key, []):
            m2 = m.copy()
            m2['Хозяева'] = home
            m2['Гости'] = away
            m2['Фора по очкам'] = -m['Фора по очкам']
            current_h2h.append(m2)
        if current_h2h:
            df_h2h = pd.DataFrame(current_h2h)
            st.subheader(f"История встреч: {home} – {away}")
            st.dataframe(df_h2h[['Дата','Хозяева','Гости','Счёт по сетам','Фора по очкам']])
            if st.button("Очистить историю этой пары"):
                st.session_state.h2h_manual.pop(key_pair, None)
                st.session_state.h2h_manual.pop(rev_key, None)
                st.rerun()
        else:
            st.info("Нет данных о личных встречах. Добавьте вручную.")

        if st.button("Рассчитать котировки", key="calc"):
            if home == away:
                st.error("Выберите разные команды")
            else:
                # --- Прогноз по сетам ---
                p_home = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
                p_away = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
                prob_home_match = prob_win_match(p_home)
                prob_away_match = prob_win_match(p_away)
                total = prob_home_match + prob_away_match
                prob_home_norm = prob_home_match / total
                prob_away_norm = prob_away_match / total
                if prob_home_norm > prob_away_norm:
                    favorite = home
                    fav_prob = prob_home_norm
                else:
                    favorite = away
                    fav_prob = prob_away_norm
                margin = 0.05
                odds = (1 - margin) / fav_prob
                st.subheader("📈 Прогноз по сетам")
                st.write(f"**Победа {favorite} – коэффициент {odds:.2f}**")
                st.caption("Вероятность победы в матче рассчитана через биномиальное распределение (best of 5) и нормализована.")

                # --- Прогноз по очкам с учётом чекбокса вычитания H2H ---
                home_data = {
                    'name': home,
                    'sets_w': h_sv, 'sets_l': h_sp,
                    'pts_w': h_bv, 'pts_l': h_bp,
                    'matches': h_matches
                }
                away_data = {
                    'name': away,
                    'sets_w': a_sv, 'sets_l': a_sp,
                    'pts_w': a_bv, 'pts_l': a_bp,
                    'matches': a_matches
                }
                
                if subtract_h2h and h2h_encounters:
                    raw_handicap, h_adj_m, a_adj_m = compute_raw_handicap_with_h2h(home_data, away_data, h2h_encounters)
                    matches_info = f"Матчей после вычета H2H: хозяева – {h_adj_m}, гости – {a_adj_m}"
                else:
                    raw_handicap, h_adj_m, a_adj_m = compute_raw_handicap_without_h2h(home_data, away_data)
                    matches_info = f"Исходное количество матчей: хозяева – {h_adj_m}, гости – {a_adj_m}"
                
                min_matches = min(h_adj_m, a_adj_m)
                
                # Выбор корректирующей функции
                if gender == "Мужчины":
                    if min_matches == 2:
                        adjusted = adjust_handicap_men_2matches(raw_handicap)
                        corr_type = "мужской (2 игры)"
                    elif min_matches == 3:
                        adjusted = adjust_handicap_men_3matches(raw_handicap)
                        corr_type = "мужской (3 игры)"
                    else:
                        if neutral_field:
                            adjusted = adjust_handicap_men_neutral(raw_handicap)
                            corr_type = "мужской нейтральной"
                        else:
                            adjusted = adjust_handicap_men_home(raw_handicap)
                            corr_type = "мужской домашней"
                else:
                    if min_matches == 2:
                        adjusted = adjust_handicap_women_2matches(raw_handicap)
                        corr_type = "женской (2 игры)"
                    elif min_matches == 3:
                        adjusted = adjust_handicap_women_3matches(raw_handicap)
                        corr_type = "женской (3 игры)"
                    else:
                        if neutral_field:
                            adjusted = adjust_handicap_women_neutral(raw_handicap)
                            corr_type = "женской нейтральной"
                        else:
                            adjusted = adjust_handicap_women_home(raw_handicap)
                            corr_type = "женской домашней"
                
                st.subheader("⚖️ Прогноз по очкам (скорректированный)")
                if adjusted > 0:
                    st.success(f"Фора на матч: {adjusted:.1f} (в пользу хозяев)")
                elif adjusted < 0:
                    st.success(f"Фора на матч: {adjusted:.1f} (в пользу гостей)")
                else:
                    st.info("Фора близка к нулю")
                st.caption(f"Исходная фора (сырая): {raw_handicap:.1f}\n{matches_info}\nСкорректировано по {corr_type} таблице")
else:
    if st.session_state.df_teams is not None and st.session_state.df_teams.empty:
        st.warning("Активная таблица пуста")
    else:
        st.info("Выберите источник данных и загрузите команды.")
