import streamlit as st
import pandas as pd
import re
import math
import json
import requests
from bs4 import BeautifulSoup
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# ==================== КОРРЕКТИРОВКИ ФОРЫ (БЕЗ ИЗМЕНЕНИЙ) ====================
# (все 8 функций adjust_handicap_* здесь не приводятся для краткости, но они должны быть.
# Они полностью идентичны предыдущим версиям. Если у вас их нет, возьмите из предыдущего полного кода.
# Для экономии места они опущены, но в реальном файле они обязательно должны присутствовать.
# Вы можете скопировать их из предыдущего ответа или я пришлю отдельно.)

# ==================== ОБЩИЕ ФУНКЦИИ ====================
def prob_win_match(p: float, best_of: int = 5) -> float:
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
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

# ==================== ПАРСЕР ТАБЛИЦ (CSV, EXCEL, ТЕКСТ) – ОСТАЁТСЯ БЕЗ ИЗМЕНЕНИЙ ====================
# (функции parse_table_to_df, parse_text_to_df – такие же, как в предыдущей полной версии.
# Чтобы не дублировать, они здесь не приведены. В вашем файле они уже есть.

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ DATA PROJECT И URL ====================
# (остаются без изменений – не приводятся для краткости)

# ==================== ОСНОВНОЙ КОД STREAMLIT ====================

st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None
if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}   # структура: (team1, team2) -> список встреч, каждая с полями 'sets', 'points', 'date'
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

# ==================== БОКОВАЯ ПАНЕЛЬ (ТАБЛИЦЫ) – БЕЗ ИЗМЕНЕНИЙ ====================
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
        url = st.text_input(
            "Введите URL страницы с результатами",
            placeholder="https://volley.ru/... или https://...dataproject.com/CompetitionStandings.aspx?ID=127"
        )
        combine = False
        if "dataproject.com" in url:
            combine = st.checkbox("Складывать все этапы (только для Data Project)", value=False)
            if combine:
                st.caption("Будут автоматически найдены и просуммированы все этапы на странице (1ª Fase, плей-офф и т.д.).")
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
            "Категория",
            ["Мужчины", "Женщины"],
            index=0 if st.session_state.detected_gender == "Мужчины" else 1,
            help="Можно изменить вручную."
        )
        neutral_field = st.checkbox("Нейтральное поле", help="Для малых выборок (2-3 игры) формулы одинаковы")
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
            h_matches = home_row['Матчи'] if 'Матчи' in home_row and pd.notna(home_row['Матчи']) else None
            p_home_set = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
            matches_info = f" | Матчей: {h_matches}" if h_matches else ""
            st.caption(f"Сеты: {h_sv}:{h_sp} | Мячи: {h_bv}:{h_bp} | % сетов: {p_home_set:.1%}{matches_info}")
        with col2:
            away_index = teams.index(st.session_state.away_team) if st.session_state.away_team in teams else 1 if len(teams)>1 else 0
            away = st.selectbox("Гостевая", teams, index=away_index, key="away_sel")
            st.session_state.away_team = away
            away_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
            a_sets_str = away_row['Сеты']
            a_points_str = away_row['Мячи']
            a_sv, a_sp = map(int, a_sets_str.split(':'))
            a_bv, a_bp = map(int, a_points_str.split(':'))
            a_matches = away_row['Матчи'] if 'Матчи' in away_row and pd.notna(away_row['Матчи']) else None
            p_away_set = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
            matches_info = f" | Матчей: {a_matches}" if a_matches else ""
            st.caption(f"Сеты: {a_sv}:{a_sp} | Мячи: {a_bv}:{a_bp} | % сетов: {p_away_set:.1%}{matches_info}")

        # ----- Личные встречи (ручной ввод, обновлённый) -----
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
                sets_h2h = st.text_input("Счёт по сетам", placeholder="3:1 (обязательно)")
            pts_h2h = st.text_input("Счёт по очкам", placeholder="75:70 (обязательно)")
            date_h2h = st.text_input("Дата", placeholder="01.01.2026")
            if st.button("Добавить", key="add_h2h"):
                error = None
                if not sets_h2h.strip():
                    error = "Укажите счёт по сетам"
                elif not pts_h2h.strip():
                    error = "Укажите счёт по очкам"
                else:
                    # валидация счёта по сетам
                    if ':' not in sets_h2h:
                        error = "Счёт по сетам должен содержать двоеточие, например 3:1"
                    else:
                        parts = sets_h2h.split(':')
                        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                            error = "Счёт по сетам должен состоять из двух чисел"
                    if not error:
                        # валидация счёта по очкам
                        if ':' not in pts_h2h:
                            error = "Счёт по очкам должен содержать двоеточие, например 75:70"
                        else:
                            p_parts = pts_h2h.split(':')
                            if len(p_parts) != 2:
                                error = "Счёт по очкам должен состоять из двух чисел"
                            else:
                                try:
                                    p1 = int(p_parts[0])
                                    p2 = int(p_parts[1])
                                except:
                                    error = "Счёт по очкам должен содержать целые числа"
                if error:
                    st.error(error)
                else:
                    # вычисляем фору по очкам (разница) в пользу хозяев
                    p1, p2 = map(int, pts_h2h.split(':'))
                    force = p1 - p2
                    key = (hh, ha)
                    st.session_state.h2h_manual.setdefault(key, []).append({
                        'Дата': date_h2h or "(нет даты)",
                        'Хозяева': hh,
                        'Гости': ha,
                        'Счёт по сетам': sets_h2h,
                        'Счёт по очкам': pts_h2h,
                        'Фора по очкам': force
                    })
                    st.success("Добавлено")
                    st.rerun()

        # Формируем список встреч для выбранной пары home-away
        key_pair = (home, away)
        rev_key = (away, home)
        current_h2h = []
        for m in st.session_state.h2h_manual.get(key_pair, []):
            current_h2h.append(m)
        for m in st.session_state.h2h_manual.get(rev_key, []):
            m2 = m.copy()
            m2['Хозяева'] = home
            m2['Гости'] = away
            m2['Счёт по сетам'] = m['Счёт по сетам']  # счёт в формате "3:1" – нужно поменять местами? Для обратной встречи счёт меняется
            # меняем счёт сетов и очков местами
            sets_parts = m['Счёт по сетам'].split(':')
            m2['Счёт по сетам'] = f"{sets_parts[1]}:{sets_parts[0]}"
            pts_parts = m['Счёт по очкам'].split(':')
            m2['Счёт по очкам'] = f"{pts_parts[1]}:{pts_parts[0]}"
            m2['Фора по очкам'] = -m['Фора по очкам']
            current_h2h.append(m2)
        if current_h2h:
            st.subheader(f"История встреч: {home} – {away}")
            display_data = []
            for m in current_h2h:
                display_data.append({
                    'Дата': m['Дата'],
                    'Хозяева': m['Хозяева'],
                    'Гости': m['Гости'],
                    'Счёт по сетам': m['Счёт по сетам'],
                    'Счёт по очкам': m['Счёт по очкам']
                })
            st.dataframe(pd.DataFrame(display_data))
            if st.button("Очистить историю этой пары"):
                st.session_state.h2h_manual.pop(key_pair, None)
                st.session_state.h2h_manual.pop(rev_key, None)
                st.rerun()
        else:
            st.info("Нет данных о личных встречах. Добавьте вручную, указав счёт по сетам и по очкам.")

        # ----- Расчёт прогноза -----
        # Чекбокс для учёта личных встреч
        use_h2h = st.checkbox("Учитывать личные встречи (включено – усреднение, выключено – исключение из статистики)", value=True)

        if st.button("Рассчитать котировки", key="calc"):
            if home == away:
                st.error("Выберите разные команды")
            else:
                # Исходные данные
                h_sv_orig, h_sp_orig = h_sv, h_sp
                h_bv_orig, h_bp_orig = h_bv, h_bp
                h_matches_orig = h_matches
                a_sv_orig, a_sp_orig = a_sv, a_sp
                a_bv_orig, a_bp_orig = a_bv, a_bp
                a_matches_orig = a_matches

                # Если есть личные встречи и нужно их исключить
                if not use_h2h and current_h2h:
                    # Вычитаем из статистики каждой команды данные личных встреч
                    # Суммируем сеты и очки для каждой команды по всем личным встречам (в формате home vs away)
                    h_sets_w_sub = 0
                    h_sets_l_sub = 0
                    h_pts_w_sub = 0
                    h_pts_l_sub = 0
                    a_sets_w_sub = 0
                    a_sets_l_sub = 0
                    a_pts_w_sub = 0
                    a_pts_l_sub = 0
                    for match in current_h2h:
                        # Для home (хозяева в этом матче)
                        sets_parts = match['Счёт по сетам'].split(':')
                        h_sets_w_sub += int(sets_parts[0])
                        h_sets_l_sub += int(sets_parts[1])
                        pts_parts = match['Счёт по очкам'].split(':')
                        h_pts_w_sub += int(pts_parts[0])
                        h_pts_l_sub += int(pts_parts[1])
                        # Для away (гости)
                        a_sets_w_sub += int(sets_parts[1])
                        a_sets_l_sub += int(sets_parts[0])
                        a_pts_w_sub += int(pts_parts[1])
                        a_pts_l_sub += int(pts_parts[0])
                    # Количество матчей между этими командами
                    n_h2h = len(current_h2h)
                    # Вычитаем из общей статистики
                    h_sv = h_sv_orig - h_sets_w_sub
                    h_sp = h_sp_orig - h_sets_l_sub
                    h_bv = h_bv_orig - h_pts_w_sub
                    h_bp = h_bp_orig - h_pts_l_sub
                    h_matches = h_matches_orig - n_h2h
                    a_sv = a_sv_orig - a_sets_w_sub
                    a_sp = a_sp_orig - a_sets_l_sub
                    a_bv = a_bv_orig - a_pts_w_sub
                    a_bp = a_bp_orig - a_pts_l_sub
                    a_matches = a_matches_orig - n_h2h
                    # Проверяем, чтобы не было отрицательных значений
                    for var, name in [(h_sv, 'home sets won'), (h_sp, 'home sets lost'), (h_bv, 'home points won'),
                                      (h_bp, 'home points lost'), (h_matches, 'home matches'),
                                      (a_sv, 'away sets won'), (a_sp, 'away sets lost'), (a_bv, 'away points won'),
                                      (a_bp, 'away points lost'), (a_matches, 'away matches')]:
                        if var < 0:
                            st.warning(f"Некорректное вычитание: {name} стало отрицательным. Возможно, личные встречи уже учтены в общей статистике? Будет использована исходная статистика.")
                            # Откатываем изменения
                            h_sv, h_sp = h_sv_orig, h_sp_orig
                            h_bv, h_bp = h_bv_orig, h_bp_orig
                            h_matches = h_matches_orig
                            a_sv, a_sp = a_sv_orig, a_sp_orig
                            a_bv, a_bp = a_bv_orig, a_bp_orig
                            a_matches = a_matches_orig
                            break
                else:
                    # Используем исходные данные
                    h_sv, h_sp = h_sv_orig, h_sp_orig
                    h_bv, h_bp = h_bv_orig, h_bp_orig
                    h_matches = h_matches_orig
                    a_sv, a_sp = a_sv_orig, a_sp_orig
                    a_bv, a_bp = a_bv_orig, a_bp_orig
                    a_matches = a_matches_orig

                if h_matches is None or a_matches is None:
                    st.warning("Для расчёта форы по очкам необходимо указать количество сыгранных матчей для обеих команд. Прогноз по сетам будет рассчитан.")

                # Прогноз по сетам (на основе скорректированных данных, если исключали)
                p_home = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
                p_away = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
                best_of = 3 if match_format.startswith("до 2") else 5
                prob_home_match = prob_win_match(p_home, best_of)
                prob_away_match = prob_win_match(p_away, best_of)
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
                st.caption(f"Вероятность победы в матче через биномиальное распределение (best-of-{best_of}), нормализована.")

                # Прогноз по очкам
                if h_matches is not None and a_matches is not None and h_matches > 0 and a_matches > 0:
                    # Сырая фора на основе скорректированных данных (если исключали, то уже без H2H)
                    raw_handicap = calculate_raw_handicap(
                        h_sv, h_sp, h_bv, h_bp, h_matches,
                        a_sv, a_sp, a_bv, a_bp, a_matches
                    )
                    # Если есть личные встречи и чекбокс включён, то усредняем
                    avg_h2h_force = None
                    if use_h2h and current_h2h:
                        forces = [m['Фора по очкам'] for m in current_h2h]
                        if forces:
                            avg_h2h_force = sum(forces) / len(forces)
                    if avg_h2h_force is not None:
                        # Усредняем исходную фору и среднюю фору из личных встреч
                        final_raw = (raw_handicap + avg_h2h_force) / 2
                        st.caption(f"Сырая фора по общей статистике: {raw_handicap:.1f}, средняя фора из личных встреч: {avg_h2h_force:.1f}. После усреднения: {final_raw:.1f}")
                    else:
                        final_raw = raw_handicap
                        if not use_h2h and current_h2h:
                            st.caption(f"Личные встречи исключены из статистики, фора пересчитана. Сырая фора: {final_raw:.1f}")
                        elif current_h2h:
                            st.caption(f"Личные встречи не учитываются (чекбокс выключен). Сырая фора: {final_raw:.1f}")
                        else:
                            st.caption(f"Личные встречи отсутствуют. Сырая фора: {final_raw:.1f}")

                    # Применяем корректировки adjust_handicap_* на основе final_raw
                    min_matches = min(h_matches, a_matches)
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
                    st.info("Для расчёта форы по очкам укажите количество матчей для обеих команд (колонка 'Матчи' в таблице).")
else:
    if st.session_state.df_teams is not None and st.session_state.df_teams.empty:
        st.warning("Активная таблица пуста")
    else:
        st.info("Выберите источник данных и загрузите команды.")
