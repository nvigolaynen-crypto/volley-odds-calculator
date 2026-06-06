import streamlit as st
import pandas as pd
import re
import math
import json
import requests
from bs4 import BeautifulSoup

# ==================== ВСЕ ФУНКЦИИ КОРРЕКТИРОВКИ ФОРЫ (без изменений) ====================
# (они такие же, как в предыдущих версиях – не приводятся для краткости, но в полном файле они есть)
# Для экономии места здесь они опущены. В конце ответа я дам ссылку на полный код или вы можете
# скопировать их из предыдущего сообщения. В этом ответе я сосредоточусь на ключевых изменениях.

def adjust_handicap_men_home(handicap: float) -> float: pass  # заглушка
def adjust_handicap_men_neutral(handicap: float) -> float: pass
def adjust_handicap_women_home(handicap: float) -> float: pass
def adjust_handicap_women_neutral(handicap: float) -> float: pass
def adjust_handicap_men_2(handicap: float) -> float: pass
def adjust_handicap_women_2(handicap: float) -> float: pass
def adjust_handicap_men_3(handicap: float) -> float: pass
def adjust_handicap_women_3(handicap: float) -> float: pass
# (реальные реализации должны быть в вашем файле)

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

# ==================== ПАРСЕРЫ (без изменений, они уже есть) ====================
# parse_table_to_df, parse_text_to_df, data project parsers – оставляем как в предыдущем полном коде.
# Чтобы не дублировать, здесь они опущены.

# ==================== STREAMLIT APP (основная часть с изменениями) ====================
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Инициализация session_state (как в предыдущих версиях)
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

# Боковая панель (таблицы) – без изменений (код есть в предыдущем ответе)
# Здесь она не повторяется для краткости.

# Основная область (выбор источника) – без изменений.

# ---------- Блок прогноза (с упрощённым вводом личных встреч) ----------
if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
    if 'Команда' not in st.session_state.df_teams.columns:
        st.error("Некорректный формат: отсутствует колонка 'Команда'")
    else:
        teams = st.session_state.df_teams['Команда'].tolist()
        st.subheader("📊 Прогноз на матч")
        gender = st.radio("Категория", ["Мужчины", "Женщины"], index=0 if st.session_state.detected_gender == "Мужчины" else 1)
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
                # Счёт по сетам – опционально, только для отображения
                sets_h2h = st.text_input("Счёт по сетам (опционально)", placeholder="3:1")
            pts_input = st.text_input("Счёт по очкам (разница или счёт команд)", placeholder="75:41 или 75 41 или 34")
            date_h2h = st.text_input("Дата", placeholder="01.01.2026")
            if st.button("Добавить", key="add_h2h"):
                has_sets = bool(sets_h2h.strip())
                has_pts = bool(pts_input.strip())
                if not has_pts:
                    st.error("Укажите счёт по очкам (разницу или счёт команд)")
                else:
                    error = None
                    force = None
                    pts_display = None
                    # Парсим ввод: может быть "75:41", "75 41", "75-41" или просто число
                    pts_clean = pts_input.strip().replace(',', '.')
                    if ':' in pts_clean:
                        p_parts = pts_clean.split(':')
                        if len(p_parts) != 2:
                            error = "Неверный формат. Используйте 75:41 или 75 41"
                        else:
                            try:
                                p1 = float(p_parts[0])
                                p2 = float(p_parts[1])
                                force = p1 - p2
                                pts_display = f"{p1:.0f}:{p2:.0f}" if p1.is_integer() and p2.is_integer() else f"{p1}:{p2}"
                            except:
                                error = "Очки должны быть числами"
                    elif ' ' in pts_clean:
                        p_parts = pts_clean.split()
                        if len(p_parts) != 2:
                            error = "Неверный формат. Используйте 75 41"
                        else:
                            try:
                                p1 = float(p_parts[0])
                                p2 = float(p_parts[1])
                                force = p1 - p2
                                pts_display = f"{p1:.0f}:{p2:.0f}" if p1.is_integer() and p2.is_integer() else f"{p1}:{p2}"
                            except:
                                error = "Очки должны быть числами"
                    elif '-' in pts_clean:
                        p_parts = pts_clean.split('-')
                        if len(p_parts) != 2:
                            error = "Неверный формат. Используйте 75-41"
                        else:
                            try:
                                p1 = float(p_parts[0])
                                p2 = float(p_parts[1])
                                force = p1 - p2
                                pts_display = f"{p1:.0f}:{p2:.0f}" if p1.is_integer() and p2.is_integer() else f"{p1}:{p2}"
                            except:
                                error = "Очки должны быть числами"
                    else:
                        # Просто число – разница
                        try:
                            force = float(pts_clean)
                            pts_display = pts_clean
                        except:
                            error = "Введите число (разницу) или счёт через двоеточие/пробел/дефис"
                    if error:
                        st.error(error)
                    else:
                        # Проверка счёта по сетам (если указан)
                        if has_sets:
                            if ':' not in sets_h2h:
                                st.error("Счёт по сетам должен содержать двоеточие, например 3:1")
                                continue
                            parts = sets_h2h.split(':')
                            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                                st.error("Счёт по сетам должен состоять из двух чисел")
                                continue
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
            if m['Счёт по очкам'] and m['Фора по очкам'] is not None:
                m2['Фора по очкам'] = -m['Фора по очкам']
                # Меняем отображение счёта
                if ':' in m['Счёт по очкам']:
                    pts_parts = m['Счёт по очкам'].split(':')
                    m2['Счёт по очкам'] = f"{pts_parts[1]}:{pts_parts[0]}"
                else:
                    m2['Счёт по очкам'] = str(-float(m['Счёт по очкам']))
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
            st.info("Нет данных о личных встречах. Добавьте хотя бы счёт по очкам.")

        # ----- Расчёт прогноза -----
        use_h2h = st.checkbox("Учитывать личные встречи (включено – усреднение, выключено – вычитание из статистики)", value=True)

        if st.button("Рассчитать котировки", key="calc"):
            if home == away:
                st.error("Выберите разные команды")
            else:
                # 1. Полная статистика
                h_sv_full, h_sp_full = h_sv, h_sp
                h_bv_full, h_bp_full = h_bv, h_bp
                h_matches_full = h_matches
                a_sv_full, a_sp_full = a_sv, a_sp
                a_bv_full, a_bp_full = a_bv, a_bp
                a_matches_full = a_matches

                # 2. Полная фора
                full_raw = None
                if h_matches_full and a_matches_full and h_matches_full > 0 and a_matches_full > 0:
                    full_raw = calculate_raw_handicap(
                        h_sv_full, h_sp_full, h_bv_full, h_bp_full, h_matches_full,
                        a_sv_full, a_sp_full, a_bv_full, a_bp_full, a_matches_full
                    )

                # 3. Очищенная статистика (вычитаем только очки и матчи, сеты не трогаем)
                h_bv_clean, h_bp_clean = h_bv_full, h_bp_full
                h_matches_clean = h_matches_full
                a_bv_clean, a_bp_clean = a_bv_full, a_bp_full
                a_matches_clean = a_matches_full
                h_sv_clean, h_sp_clean = h_sv_full, h_sp_full  # сеты не меняем
                a_sv_clean, a_sp_clean = a_sv_full, a_sp_full
                subtracted = 0
                for match in current_h2h:
                    # Для вычитания нужна фора (разница) и количество встреч
                    if match['Фора по очкам'] is not None:
                        # Чтобы вычесть, нужно знать абсолютные очки каждой команды. Если есть полный счёт – используем его.
                        # Если нет – оцениваем по средней разнице? Нельзя. Поэтому будем вычитать только количество матчей,
                        # а очки не вычитаем, так как неизвестны абсолютные значения.
                        # Это компромисс: при вычитании личных встреч мы не можем изменить очки, если нет полного счёта.
                        # Но поскольку пользователь ввёл только разницу, мы можем вычесть только матчи, а очки оставить – это исказит средние.
                        # Лучше требовать полный счёт для вычитания. Но пользователь не хочет вводить полный счёт.
                        # Поэтому я сделаю так: если введена разница, то для вычитания мы вычитаем только количество матчей,
                        # а очки оставляем. Тогда очищенная фора будет считаться без учёта изменения очков.
                        # Это не идеально, но единственный вариант без ввода полных очков.
                        # Для усреднения разница используется нормально.
                        # Предупрежу пользователя.
                        if ':' not in str(match['Счёт по очкам']):
                            st.warning(f"Для встречи {match['Хозяева']} - {match['Гости']} указана только разница, без полного счёта. При вычитании будут учтены только матчи, но не очки.")
                        else:
                            # Есть полный счёт – вычитаем и очки
                            pts_parts = match['Счёт по очкам'].split(':')
                            h_bv_clean -= int(pts_parts[0])
                            h_bp_clean -= int(pts_parts[1])
                            a_bv_clean -= int(pts_parts[1])
                            a_bp_clean -= int(pts_parts[0])
                        # В любом случае вычитаем матч
                        h_matches_clean -= 1
                        a_matches_clean -= 1
                        subtracted += 1
                if subtracted > 0:
                    if h_matches_clean <= 0 or a_matches_clean <= 0:
                        st.warning("После вычитания количество матчей стало нулевым. Использую полную статистику.")
                        h_matches_clean, a_matches_clean = h_matches_full, a_matches_full
                        h_bv_clean, h_bp_clean = h_bv_full, h_bp_full
                        a_bv_clean, a_bp_clean = a_bv_full, a_bp_full
                        subtracted = 0

                # 4. Фора по очищенной статистике
                clean_raw = None
                if h_matches_clean and a_matches_clean and h_matches_clean > 0 and a_matches_clean > 0:
                    clean_raw = calculate_raw_handicap(
                        h_sv_clean, h_sp_clean, h_bv_clean, h_bp_clean, h_matches_clean,
                        a_sv_clean, a_sp_clean, a_bv_clean, a_bp_clean, a_matches_clean
                    )

                # 5. Средняя фора из личных встреч
                h2h_forces = [m['Фора по очкам'] for m in current_h2h if m['Фора по очкам'] is not None]
                avg_h2h = sum(h2h_forces) / len(h2h_forces) if h2h_forces else None

                # 6. Выбор режима
                if use_h2h:
                    if full_raw is not None and avg_h2h is not None:
                        final_raw = (full_raw + avg_h2h) / 2
                        st.info(f"📊 Режим С УЧЁТОМ личных встреч\nПолная фора: {full_raw:.2f}\nСредняя фора личек: {avg_h2h:.2f}\n→ Итоговая: {final_raw:.2f}")
                    elif full_raw is not None:
                        final_raw = full_raw
                        st.info(f"Режим С УЧЁТОМ личных встреч, но нет форы по личкам → полная фора: {final_raw:.2f}")
                    elif avg_h2h is not None:
                        final_raw = avg_h2h
                        st.info(f"Режим С УЧЁТОМ личных встреч, но нет общей статистики → средняя фора личек: {final_raw:.2f}")
                    else:
                        final_raw = None
                        st.error("Нет данных для расчёта форы")
                else:
                    if clean_raw is not None and avg_h2h is not None:
                        final_raw = (clean_raw + avg_h2h) / 2
                        st.info(f"📊 Режим БЕЗ УЧЁТА личных встреч\nФора после вычитания {subtracted} встреч: {clean_raw:.2f}\nСредняя фора личек: {avg_h2h:.2f}\n→ Итоговая: {final_raw:.2f}")
                    elif clean_raw is not None:
                        final_raw = clean_raw
                        st.info(f"Режим БЕЗ УЧЁТА личных встреч, но нет форы по личкам → очищенная фора: {final_raw:.2f}")
                    elif avg_h2h is not None:
                        final_raw = avg_h2h
                        st.info(f"Режим БЕЗ УЧЁТА личных встреч, но нет очищенной статистики → средняя фора личек: {final_raw:.2f}")
                    else:
                        final_raw = None
                        st.error("Нет данных для расчёта форы")

                # 7. Прогноз по сетам (на основе полной статистики)
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

                # 8. Прогноз по очкам с корректировкой
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
                    st.caption(f"Исходная сырая фора: {final_raw:.1f} → скорректировано по {formula}")
                else:
                    st.info("Не удалось рассчитать фору по очкам. Убедитесь, что указано количество матчей.")
else:
    st.info("Выберите источник данных и загрузите команды.")
