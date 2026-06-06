import streamlit as st
import math

# ==================== ФУНКЦИИ КОРРЕКТИРОВКИ ФОРЫ (заглушки) ====================
def adjust_handicap_men_home(x): return x
def adjust_handicap_men_neutral(x): return x
def adjust_handicap_women_home(x): return x
def adjust_handicap_women_neutral(x): return x
def adjust_handicap_men_2(x): return x
def adjust_handicap_women_2(x): return x
def adjust_handicap_men_3(x): return x
def adjust_handicap_women_3(x): return x

# ==================== ФУНКЦИЯ РАСЧЁТА ФОРЫ ====================
def calculate_raw_handicap(h_pts_w, h_pts_l, h_matches, a_pts_w, a_pts_l, a_matches):
    if h_matches is None or a_matches is None or h_matches <= 0 or a_matches <= 0:
        return None
    home_avg_scored = h_pts_w / h_matches
    home_avg_conceded = h_pts_l / h_matches
    away_avg_scored = a_pts_w / a_matches
    away_avg_conceded = a_pts_l / a_matches
    expected_home = (home_avg_scored + away_avg_conceded) / 2
    expected_away = (away_avg_scored + home_avg_conceded) / 2
    return expected_home - expected_away

# ==================== STREAMLIT APP ====================
st.set_page_config(page_title="Тест личных встреч", layout="wide")
st.title("Тест расчёта прогноза по очкам")

# ----- Ручной ввод статистики команд -----
st.subheader("1. Статистика команд (все матчи)")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Домашняя команда**")
    h_name = st.text_input("Название", "Команда А")
    h_pts_w = st.number_input("Набрано очков", 1500, step=10)
    h_pts_l = st.number_input("Пропущено очков", 1400, step=10)
    h_matches = st.number_input("Количество матчей", 30, step=1)
with col2:
    st.markdown("**Гостевая команда**")
    a_name = st.text_input("Название", "Команда Б")
    a_pts_w = st.number_input("Набрано очков", 1450, step=10)
    a_pts_l = st.number_input("Пропущено очков", 1550, step=10)
    a_matches = st.number_input("Количество матчей", 30, step=1)

# ----- Личные встречи -----
st.subheader("2. Личные встречи")
# Хранилище
if 'test_h2h' not in st.session_state:
    st.session_state.test_h2h = []

# Отображение текущих встреч
if st.session_state.test_h2h:
    st.write("Список добавленных встреч:")
    for i, m in enumerate(st.session_state.test_h2h):
        st.write(f"{i+1}. {m['Хозяева']} - {m['Гости']}: счёт по очкам {m['Счёт по очкам']}, разница {m['Фора']}")
    if st.button("Очистить все встречи"):
        st.session_state.test_h2h = []
        st.rerun()

# Форма добавления новой встречи
with st.form("add_h2h"):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        hh = st.text_input("Хозяева", "Команда А")
    with col_b:
        ha = st.text_input("Гости", "Команда Б")
    with col_c:
        pts_input = st.text_input("Счёт по очкам (в формате 75:41 или просто разница 34)", "75:41")
    if st.form_submit_button("Добавить встречу"):
        if not pts_input.strip():
            st.error("Введите счёт по очкам")
        else:
            if ':' in pts_input:
                parts = pts_input.split(':')
                if len(parts) != 2:
                    st.error("Неверный формат, используйте 75:41")
                else:
                    try:
                        p1 = float(parts[0])
                        p2 = float(parts[1])
                        force = p1 - p2
                        display = pts_input
                        full_score = True
                    except:
                        st.error("Очки должны быть числами")
                        full_score = False
            else:
                try:
                    force = float(pts_input)
                    display = pts_input
                    full_score = False
                except:
                    st.error("Введите число (разницу) или счёт через двоеточие")
            if 'force' in locals():
                st.session_state.test_h2h.append({
                    'Хозяева': hh,
                    'Гости': ha,
                    'Счёт по очкам': display,
                    'Фора': force,
                    'full_score': full_score
                })
                st.success("Добавлено")
                st.rerun()

# ----- Расчёт прогноза -----
st.subheader("3. Расчёт прогноза")
use_h2h = st.checkbox("Учитывать личные встречи (включено – усреднение, выключено – вычитание из статистики)", value=True)

if st.button("Рассчитать"):
    # Полная фора
    full_raw = calculate_raw_handicap(h_pts_w, h_pts_l, h_matches, a_pts_w, a_pts_l, a_matches)
    if full_raw is None:
        st.error("Не хватает данных для расчёта полной форы")
    else:
        st.write(f"**Полная фора** (по всем матчам): {full_raw:.2f}")

    # Очищенная статистика (вычитаем только встречи с полным счётом)
    h_pts_w_clean = h_pts_w
    h_pts_l_clean = h_pts_l
    h_matches_clean = h_matches
    a_pts_w_clean = a_pts_w
    a_pts_l_clean = a_pts_l
    a_matches_clean = a_matches
    subtracted = 0
    for match in st.session_state.test_h2h:
        if match.get('full_score', False):
            # Вычитаем очки
            pts_parts = match['Счёт по очкам'].split(':')
            h_pts_w_clean -= int(pts_parts[0])
            h_pts_l_clean -= int(pts_parts[1])
            a_pts_w_clean -= int(pts_parts[1])
            a_pts_l_clean -= int(pts_parts[0])
            # Вычитаем матчи
            h_matches_clean -= 1
            a_matches_clean -= 1
            subtracted += 1
    if subtracted > 0:
        if h_matches_clean <= 0 or a_matches_clean <= 0:
            st.warning("После вычитания количество матчей стало неположительным. Использую полную статистику.")
            h_pts_w_clean, h_pts_l_clean = h_pts_w, h_pts_l
            h_matches_clean = h_matches
            a_pts_w_clean, a_pts_l_clean = a_pts_w, a_pts_l
            a_matches_clean = a_matches
            subtracted = 0
    clean_raw = None
    if h_matches_clean > 0 and a_matches_clean > 0:
        clean_raw = calculate_raw_handicap(h_pts_w_clean, h_pts_l_clean, h_matches_clean,
                                           a_pts_w_clean, a_pts_l_clean, a_matches_clean)
    if clean_raw is not None:
        st.write(f"**Очищенная фора** (после вычитания {subtracted} встреч с полным счётом): {clean_raw:.2f}")

    # Средняя фора из личных встреч (все встречи, где есть фора)
    forces = [m['Фора'] for m in st.session_state.test_h2h]
    avg_force = sum(forces) / len(forces) if forces else None
    if avg_force is not None:
        st.write(f"**Средняя фора из личных встреч** (по {len(forces)} встречам): {avg_force:.2f}")

    # Итоговая сырая фора
    if use_h2h:
        if full_raw is not None and avg_force is not None:
            final_raw = (full_raw + avg_force) / 2
            st.info(f"Режим: **С учётом личных встреч**\n"
                    f"({full_raw:.2f} + {avg_force:.2f}) / 2 = **{final_raw:.2f}**")
        elif full_raw is not None:
            final_raw = full_raw
            st.info(f"Режим: С учётом личных встреч (нет данных по личкам) → {final_raw:.2f}")
        else:
            final_raw = None
            st.error("Нет данных")
    else:
        if clean_raw is not None and avg_force is not None:
            final_raw = (clean_raw + avg_force) / 2
            st.info(f"Режим: **Без учёта личных встреч**\n"
                    f"({clean_raw:.2f} + {avg_force:.2f}) / 2 = **{final_raw:.2f}**")
        elif clean_raw is not None:
            final_raw = clean_raw
            st.info(f"Режим: Без учёта личных встреч (нет данных по личкам) → {final_raw:.2f}")
        else:
            final_raw = None
            st.error("Нет данных")

    if final_raw is not None:
        st.subheader("Результат")
        st.success(f"**Итоговая сырая фора: {final_raw:.1f}**")
        # Здесь можно применить adjust_handicap_*, но для теста не нужно
