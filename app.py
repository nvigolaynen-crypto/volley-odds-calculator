import streamlit as st
import pandas as pd
import re
import math
import json
import requests
from bs4 import BeautifulSoup

# ==================== КОРРЕКТИРОВКИ ФОРЫ (без изменений) ====================
# (все функции adjust_handicap_... сохранены, но для краткости опущены.
# В вашем проекте они уже есть. Если нужно, добавьте из предыдущих версий.)

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

# ==================== ПАРСЕРЫ (CSV, Excel, текст) – без изменений ====================
# ... (здесь должны быть функции parse_table_to_df, parse_text_to_df, они у вас уже есть)

# ==================== ПАРСЕРЫ DATA PROJECT ====================
# ... (функции extract_team_data_from_dataproject_table, extract_all_phases, load_teams_from_url – без изменений)

# ==================== ОСНОВНОЙ КОД STREAMLIT ====================
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Инициализация session_state
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

# ==================== БОКОВАЯ ПАНЕЛЬ ====================
with st.sidebar:
    st.header("📁 Мои таблицы")
    # ... (без изменений, полный код боковой панели из предыдущей рабочей версии)

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
    # ... (без изменений)

# -------------------- 2. РУЧНОЙ ВВОД ПАРЫ --------------------
elif st.session_state.active_source == "manual_pair":
    # ... (без изменений)

# -------------------- 3. ЗАГРУЖЕННАЯ ТАБЛИЦА --------------------
elif st.session_state.active_source == "user_table":
    # ... (без изменений)

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

        # ----- Личные встречи (упрощённый ввод) -----
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
            # Единое поле для очков: можно ввести "75:70" или просто "15" (разница)
            pts_input = st.text_input("Счёт или разница по очкам (опционально)", placeholder="75:70 или 15")
            date_h2h = st.text_input("Дата", placeholder="01.01.2026")
            if st.button("Добавить", key="add_h2h"):
                has_sets = bool(sets_h2h.strip())
                has_pts = bool(pts_input.strip())
                if not (has_sets or has_pts):
                    st.error("Укажите хотя бы один параметр: счёт по сетам или счёт/разницу по очкам")
                else:
                    error = None
                    # Проверка счёта по сетам
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
                        # Определяем формат: если есть двоеточие – полный счёт, иначе – разница
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
                            # введено просто число – разница
                            try:
                                force = float(pts_input)
                                pts_display = pts_input  # сохраняем как строку
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
            if m['Счёт по сетам']:
                parts = m['Счёт по сетам'].split(':')
                m2['Счёт по сетам'] = f"{parts[1]}:{parts[0]}"
            if m['Счёт по очкам']:
                # Если была разница в виде числа, просто меняем знак
                if m['Фора по очкам'] is not None:
                    m2['Фора по очкам'] = -m['Фора по очкам']
                    # Для отображения: если исходная запись была "15", то покажем "-15"
                    if m['Счёт по очкам'].replace('-', '').isdigit():
                        m2['Счёт по очкам'] = str(-float(m['Счёт по очкам']))
                    else:
                        # полный счёт меняем местами
                        pts_parts = m['Счёт по очкам'].split(':')
                        if len(pts_parts) == 2:
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
            st.info("Нет данных о личных встречах. Добавьте вручную, указав любые данные.")

        # ----- Расчёт прогноза -----
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

                if not use_h2h and current_h2h:
                    # Вычитаем только те встречи, где есть и сеты, и очки
                    h_sets_w_sub = 0
                    h_sets_l_sub = 0
                    h_pts_w_sub = 0
                    h_pts_l_sub = 0
                    a_sets_w_sub = 0
                    a_sets_l_sub = 0
                    a_pts_w_sub = 0
                    a_pts_l_sub = 0
                    n_h2h = 0
                    for match in current_h2h:
                        if match['Счёт по сетам'] and match['Счёт по очкам'] and ':' in match['Счёт по очкам']:
                            # вычитаем только если есть полный счёт по очкам (чтобы знать очки)
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
                            n_h2h += 1
                    if n_h2h > 0:
                        h_sv = h_sv_orig - h_sets_w_sub
                        h_sp = h_sp_orig - h_sets_l_sub
                        h_bv = h_bv_orig - h_pts_w_sub
                        h_bp = h_bp_orig - h_pts_l_sub
                        h_matches = h_matches_orig - n_h2h if h_matches_orig else None
                        a_sv = a_sv_orig - a_sets_w_sub
                        a_sp = a_sp_orig - a_sets_l_sub
                        a_bv = a_bv_orig - a_pts_w_sub
                        a_bp = a_bp_orig - a_pts_l_sub
                        a_matches = a_matches_orig - n_h2h if a_matches_orig else None
                        if min(h_sv, h_sp, h_bv, h_bp, a_sv, a_sp, a_bv, a_bp) < 0 or (h_matches and h_matches < 0) or (a_matches and a_matches < 0):
                            st.warning("Некорректное вычитание: личные встречи вероятно уже учтены. Использую полную статистику.")
                            h_sv, h_sp = h_sv_orig, h_sp_orig
                            h_bv, h_bp = h_bv_orig, h_bp_orig
                            h_matches = h_matches_orig
                            a_sv, a_sp = a_sv_orig, a_sp_orig
                            a_bv, a_bp = a_bv_orig, a_bp_orig
                            a_matches = a_matches_orig
                else:
                    h_sv, h_sp = h_sv_orig, h_sp_orig
                    h_bv, h_bp = h_bv_orig, h_bp_orig
                    h_matches = h_matches_orig
                    a_sv, a_sp = a_sv_orig, a_sp_orig
                    a_bv, a_bp = a_bv_orig, a_bp_orig
                    a_matches = a_matches_orig

                # Прогноз по сетам
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
                    raw_handicap = calculate_raw_handicap(
                        h_sv, h_sp, h_bv, h_bp, h_matches,
                        a_sv, a_sp, a_bv, a_bp, a_matches
                    )
                    if use_h2h and current_h2h:
                        forces = [m['Фора по очкам'] for m in current_h2h if m['Фора по очкам'] is not None]
                        if forces:
                            avg_h2h_force = sum(forces) / len(forces)
                            final_raw = (raw_handicap + avg_h2h_force) / 2
                            st.caption(f"Сырая фора (по статистике): {raw_handicap:.1f}, средняя фора из личных встреч: {avg_h2h_force:.1f}. Усреднённая: {final_raw:.1f}")
                        else:
                            final_raw = raw_handicap
                            st.caption(f"Личные встречи есть, но фора не указана. Сырая фора: {final_raw:.1f}")
                    else:
                        final_raw = raw_handicap
                        if not use_h2h and current_h2h:
                            st.caption(f"Личные встречи исключены из статистики. Сырая фора: {final_raw:.1f}")
                        elif current_h2h:
                            st.caption(f"Личные встречи не учитываются (чекбокс выключен). Сырая фора: {final_raw:.1f}")
                        else:
                            st.caption(f"Личные встречи отсутствуют. Сырая фора: {final_raw:.1f}")

                    # Применяем корректировки adjust_handicap_* (функции должны быть определены выше)
                    # Здесь предполагается, что они есть. Если нет – добавьте из предыдущей версии.
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
    st.info("Выберите источник данных и загрузите команды.")
