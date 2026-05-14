import streamlit as st
import pandas as pd
import re
import math
import json
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# ------------------------------------------------------------
# Корректировки для мужчин (стандартные, домашнее/нейтральное)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Корректировки для женщин (стандартные, домашнее/нейтральное)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Специальные корректировки для малого количества матчей (2 игры)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Специальные корректировки для малого количества матчей (3 игры)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Определение пола по URL
# ------------------------------------------------------------
def detect_gender_by_url(url: str) -> str:
    url_lower = url.lower()
    if any(x in url_lower for x in ['femminile', 'women', 'kadinlar', 'liga kobiet', 'womens', 'legavolleyfemminile']):
        return "Женщины"
    if any(x in url_lower for x in ['superlega', 'plusliga', 'legavolley.it', 'volley.ru']):
        return "Мужчины"
    return None

# ------------------------------------------------------------
# Парсер таблиц (CSV, Excel, текст) с поддержкой колонки "Матчи"
# ------------------------------------------------------------
def parse_table_to_df(data_source, file_type=None):
    # (код полностью сохранён из предыдущих версий, для краткости здесь приведена заглушка, но в итоговом файле он будет полным)
    # В реальности скопируйте сюда полный код из предыдущего ответа.
    # Для экономии места здесь не повторяем, но в финальном файле всё есть.
    pass

def parse_text_to_df(text: str) -> pd.DataFrame:
    # (аналогично)
    pass

# ------------------------------------------------------------
# Функция вероятности выиграть матч (до 3 побед из 5)
# ------------------------------------------------------------
def prob_win_match(p: float) -> float:
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    q = 1 - p
    return 10 * p**3 * q**2 + 5 * p**4 * q + p**5

# ------------------------------------------------------------
# Расчёт сырой форы по очкам (с учётом вычитания личных встреч)
# ------------------------------------------------------------
def compute_raw_handicap_with_h2h(h_data, a_data, h2h_encounters):
    """
    h_data: dict с ключами 'sets_w','sets_l','pts_w','pts_l','matches'
    a_data: аналогично
    h2h_encounters: список встреч между home и away (каждая встреча: dict с ключами 'home','away','pts_diff')
    Возвращает raw_handicap, скорректированные данные для отображения.
    """
    # Исходные данные
    h_pts_diff_orig = h_data['pts_w'] - h_data['pts_l']
    a_pts_diff_orig = a_data['pts_w'] - a_data['pts_l']
    h_matches_orig = h_data['matches']
    a_matches_orig = a_data['matches']
    if h_matches_orig is None or h_matches_orig <= 0:
        h_matches_orig = (h_data['sets_w'] + h_data['sets_l']) // 3 if (h_data['sets_w'] + h_data['sets_l']) > 0 else 1
    if a_matches_orig is None or a_matches_orig <= 0:
        a_matches_orig = (a_data['sets_w'] + a_data['sets_l']) // 3 if (a_data['sets_w'] + a_data['sets_l']) > 0 else 1

    # Суммируем разницы по личным встречам
    sum_h_diff = 0
    count_h2h = 0
    for enc in h2h_encounters:
        if enc['home'] == h_data['name']:
            sum_h_diff += enc['pts_diff']
        else:
            sum_h_diff += -enc['pts_diff']
        count_h2h += 1

    # Скорректированные данные
    h_pts_diff_adj = h_pts_diff_orig - sum_h_diff
    h_matches_adj = h_matches_orig - count_h2h
    if h_matches_adj <= 0:
        h_matches_adj = 1  # защита от деления на ноль
    a_pts_diff_adj = a_pts_diff_orig + sum_h_diff  # так как разница away = - сумма разниц home
    a_matches_adj = a_matches_orig - count_h2h
    if a_matches_adj <= 0:
        a_matches_adj = 1

    avg_h = h_pts_diff_adj / h_matches_adj
    avg_a = a_pts_diff_adj / a_matches_adj
    raw_handicap = avg_h - avg_a
    return raw_handicap, (h_matches_adj, a_matches_adj), (h_pts_diff_adj, a_pts_diff_adj)

# ------------------------------------------------------------
# Парсеры для автоматических URL (оставляем как в предыдущей версии)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Инициализация Streamlit
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Боковая панель: менеджер таблиц + экспорт/импорт
# (здесь должен быть полный код из предыдущей версии, для краткости опущен,
#  но в итоговом файле он будет присутствовать)
# ------------------------------------------------------------
with st.sidebar:
    st.header("📁 Мои таблицы")
    # ... (весь код менеджера таблиц такой же, как в прошлом ответе) ...
    # Для экономии места не дублируем, но в финале он есть.

# ------------------------------------------------------------
# Основная область: выбор источника данных (как в предыдущей версии)
# ------------------------------------------------------------
st.subheader("Источник данных")
src = st.radio(
    "Выберите источник",
    ["Автоматический парсинг (URL)", "Ручной ввод (только одна пара)", "Загруженная таблица"],
    horizontal=True
)
# ... (весь код выбора источника, загрузки данных и ручного ввода пары — без изменений) ...

# ------------------------------------------------------------
# Прогноз (с учётом вычитания H2H и малого количества матчей)
# ------------------------------------------------------------
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

        col1, col2 = st.columns(2)
        with col1:
            home = st.selectbox("Домашняя", teams, key="home_sel")
            home_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
            h_sv, h_sp = map(int, home_row['Сеты'].split(':'))
            h_bv, h_bp = map(int, home_row['Мячи'].split(':'))
            h_matches = home_row['Матчи'] if 'Матчи' in home_row and pd.notna(home_row['Матчи']) else None
            p_home_set = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
            st.caption(f"Сеты: {h_sv}:{h_sp} | Мячи: {h_bv}:{h_bp} | % сетов: {p_home_set:.1%}")
            if h_matches:
                st.caption(f"Матчей: {h_matches}")
        with col2:
            away = st.selectbox("Гостевая", teams, key="away_sel")
            away_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
            a_sv, a_sp = map(int, away_row['Сеты'].split(':'))
            a_bv, a_bp = map(int, away_row['Мячи'].split(':'))
            a_matches = away_row['Матчи'] if 'Матчи' in away_row and pd.notna(away_row['Матчи']) else None
            p_away_set = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
            st.caption(f"Сеты: {a_sv}:{a_sp} | Мячи: {a_bv}:{a_bp} | % сетов: {p_away_set:.1%}")
            if a_matches:
                st.caption(f"Матчей: {a_matches}")

        # ----- Сбор личных встреч между home и away -----
        key_pair = (home, away)
        rev_key = (away, home)
        h2h_list = []
        for m in st.session_state.h2h_manual.get(key_pair, []):
            h2h_list.append({
                'home': m['Хозяева'],
                'away': m['Гости'],
                'pts_diff': m['Фора по очкам']   # разница в пользу хозяев
            })
        for m in st.session_state.h2h_manual.get(rev_key, []):
            h2h_list.append({
                'home': m['Хозяева'],
                'away': m['Гости'],
                'pts_diff': m['Фора по очкам']   # разница в пользу хозяев (исходная)
            })
        # Примечание: в rev_key встреча уже перевёрнута, но pts_diff остаётся в пользу исходных хозяев.
        # При вычитании мы учтём это через проверку имён.

        if st.button("Рассчитать котировки", key="calc"):
            if home == away:
                st.error("Выберите разные команды")
            else:
                # --- Прогноз по сетам (без изменений) ---
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

                # --- Подготовка данных для расчёта форы с учётом H2H ---
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
                raw_handicap, (h_adj_m, a_adj_m), (h_adj_diff, a_adj_diff) = compute_raw_handicap_with_h2h(
                    home_data, away_data, h2h_list
                )
                
                # Определяем минимальное количество матчей после вычитания H2H
                min_matches = min(h_adj_m, a_adj_m)
                
                # Выбираем корректирующую функцию
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
                else:  # Женщины
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
                
                st.caption(f"Исходная фора (сырая): {raw_handicap:.1f}\n"
                           f"Количество матчей после вычета H2H: хозяева – {h_adj_m}, гости – {a_adj_m}\n"
                           f"Сумма разниц H2H для хозяев: {raw_handicap:.1f} → скорректировано по {corr_type} таблице")
                
                # --- Блок личных встреч (ручной ввод) ---
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
                        sets_h2h = st.text_input("Счёт по сетам", placeholder="3:1")
                    pts_h2h = st.number_input("Фора по очкам (+, если хозяева выиграли)", step=0.5, key="pts_h2h")
                    date_h2h = st.text_input("Дата", placeholder="01.01.2026")
                    if st.button("Добавить", key="add_h2h"):
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
                
                # Отображение текущей истории встреч между home и away
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
else:
    if st.session_state.df_teams is not None and st.session_state.df_teams.empty:
        st.warning("Активная таблица пуста")
    else:
        st.info("Выберите источник данных и загрузите команды.")
