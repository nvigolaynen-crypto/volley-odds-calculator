import streamlit as st
import pandas as pd
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# ------------------------------------------------------------
# Функция автоматического определения парсера по URL
# ------------------------------------------------------------
def get_parser_by_url(url: str):
    if "volley.ru" in url:
        return RussiaVolleyRuParser()
    elif "dataproject.com" in url:
        return DataProjectParser()
    else:
        return None

# ------------------------------------------------------------
# Функция парсинга таблицы и получения списка команд
# ------------------------------------------------------------
def parse_teams_list(url, combine_phases):
    parser = get_parser_by_url(url)
    if parser is None:
        return None, "Ссылка не поддерживается. Используйте volley.ru или dataproject.com"
    df, error = parser.fetch_stats(url, combine_phases=combine_phases)
    if df is not None and not df.empty and 'Команда' in df.columns:
        return df, None
    else:
        return None, error or "Не удалось загрузить данные"

# ------------------------------------------------------------
# Настройка страницы
# ------------------------------------------------------------
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Инициализация состояния
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None
if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}
if 'manual_mode' not in st.session_state:
    st.session_state.manual_mode = False

# ------------------------------------------------------------
# Основная форма
# ------------------------------------------------------------
with st.form("predict_form"):
    st.subheader("Ссылка на турнирную таблицу")
    url = st.text_input(
        "URL",
        placeholder="https://volley.ru/... или https://ossrb-web.dataproject.com/CompetitionStandings.aspx?...",
        value="https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy"
    )
    
    col_checks = st.columns(2)
    with col_checks[0]:
        manual_input = st.checkbox("Ввести статистику вручную", value=st.session_state.manual_mode)
    with col_checks[1]:
        combine_phases = False
        if "dataproject.com" in url:
            combine_phases = st.checkbox("Складывать все этапы (только Data Project)", value=False)
    
    # Если пользователь переключил чекбокс ручного ввода – меняем состояние
    if manual_input != st.session_state.manual_mode:
        st.session_state.manual_mode = manual_input
        st.rerun()
    
    # Загружаем данные из парсера, если ручной режим выключен и есть URL
    if not st.session_state.manual_mode and url:
        with st.spinner("Загрузка данных..."):
            df_teams, error = parse_teams_list(url, combine_phases)
            if df_teams is not None:
                st.session_state.df_teams = df_teams
                st.success(f"Загружено {len(df_teams)} команд")
            else:
                st.error(f"Ошибка: {error}")
                st.session_state.df_teams = None
    
    # Две колонки для домашней и гостевой команды
    col_home, col_away = st.columns(2)
    
    # ---------- Домашняя команда ----------
    with col_home:
        st.subheader("ДОМАШНЯЯ КОМАНДА")
        if st.session_state.manual_mode:
            home_name = st.text_input("Название", key="home_name")
            home_sets_v = st.number_input("Sets V (выигранные сеты)", min_value=0, step=1, key="home_sets_v")
            home_sets_p = st.number_input("Sets P (проигранные сеты)", min_value=0, step=1, key="home_sets_p")
            home_balls_v = st.number_input("Balls V (выигранные очки)", min_value=0, step=1, key="home_balls_v")
            home_balls_p = st.number_input("Balls P (проигранные очки)", min_value=0, step=1, key="home_balls_p")
            home_data_ok = bool(home_name)
        else:
            if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
                teams_list = st.session_state.df_teams['Команда'].tolist()
                home_name = st.selectbox("Название", teams_list, key="home_select")
                # Получаем данные из таблицы
                home_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home_name].iloc[0]
                sets_str = home_row['Сеты']
                balls_str = home_row['Мячи']
                home_sets_v, home_sets_p = map(int, sets_str.split(':'))
                home_balls_v, home_balls_p = map(int, balls_str.split(':'))
                home_data_ok = True
            else:
                st.warning("Нет загруженных команд. Проверьте ссылку или включите ручной ввод.")
                home_name = ""
                home_sets_v = home_sets_p = home_balls_v = home_balls_p = 0
                home_data_ok = False
        
        if not st.session_state.manual_mode and st.session_state.df_teams is not None:
            st.caption(f"Сеты: {home_sets_v}:{home_sets_p} | Мячи: {home_balls_v}:{home_balls_p}")
    
    # ---------- Гостевая команда ----------
    with col_away:
        st.subheader("ГОСТЕВАЯ КОМАНДА")
        if st.session_state.manual_mode:
            away_name = st.text_input("Название", key="away_name")
            away_sets_v = st.number_input("Sets V (выигранные сеты)", min_value=0, step=1, key="away_sets_v")
            away_sets_p = st.number_input("Sets P (проигранные сеты)", min_value=0, step=1, key="away_sets_p")
            away_balls_v = st.number_input("Balls V (выигранные очки)", min_value=0, step=1, key="away_balls_v")
            away_balls_p = st.number_input("Balls P (проигранные очки)", min_value=0, step=1, key="away_balls_p")
            away_data_ok = bool(away_name)
        else:
            if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
                teams_list = st.session_state.df_teams['Команда'].tolist()
                away_name = st.selectbox("Название", teams_list, key="away_select")
                away_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away_name].iloc[0]
                sets_str = away_row['Сеты']
                balls_str = away_row['Мячи']
                away_sets_v, away_sets_p = map(int, sets_str.split(':'))
                away_balls_v, away_balls_p = map(int, balls_str.split(':'))
                away_data_ok = True
            else:
                st.warning("Нет загруженных команд.")
                away_name = ""
                away_sets_v = away_sets_p = away_balls_v = away_balls_p = 0
                away_data_ok = False
        
        if not st.session_state.manual_mode and st.session_state.df_teams is not None:
            st.caption(f"Сеты: {away_sets_v}:{away_sets_p} | Мячи: {away_balls_v}:{away_balls_p}")
    
    # Кнопка расчёта
    submitted = st.form_submit_button("Рассчитать котировки", use_container_width=True)

# ------------------------------------------------------------
# Расчёт и вывод прогнозов (после отправки формы)
# ------------------------------------------------------------
if submitted:
    if not home_data_ok or not away_data_ok:
        st.error("Заполните данные для обеих команд (названия и статистику).")
    elif home_name == away_name:
        st.error("Выберите разные команды.")
    else:
        # Прогноз по сетам
        st.subheader("📈 Прогноз по сетам")
        home_winrate = home_sets_v / (home_sets_v + home_sets_p) if (home_sets_v + home_sets_p) > 0 else 0.5
        away_winrate = away_sets_v / (away_sets_v + away_sets_p) if (away_sets_v + away_sets_p) > 0 else 0.5
        predicted_winner = home_name if home_winrate > away_winrate else away_name
        prob_home = home_winrate
        margin = 0.05
        odds_home = (1 - margin) / prob_home if prob_home > 0 else 0
        
        st.write(f"**Прогноз победителя:** {predicted_winner}")
        st.write(f"**Вероятность победы {home_name}:** {prob_home:.1%}")
        st.write(f"**Коэффициент на победу {home_name} (с маржой 5%):** {odds_home:.2f}")
        st.caption("Прогноз основан на проценте выигранных сетов.")
        
        # Прогноз по очкам (фора)
        st.subheader("⚖️ Прогноз по очкам (фора)")
        total_matches = (home_sets_v + home_sets_p) // 3 if (home_sets_v + home_sets_p) > 0 else 30
        home_avg_diff = (home_balls_v - home_balls_p) / total_matches
        away_avg_diff = (away_balls_v - away_balls_p) / total_matches
        expected_diff = home_avg_diff - away_avg_diff
        handicap = round(expected_diff, 1)
        if handicap > 0:
            st.success(f"**Фора на матч:** {handicap} (в пользу хозяев)")
        elif handicap < 0:
            st.success(f"**Фора на матч:** {handicap} (в пользу гостей)")
        else:
            st.info("Фора близка к нулю – команды примерно равны")
        st.caption("Фора рассчитана как средняя разница очков за матч (хозяева − гости).")
        
        # ----- Личные встречи (оставляем для истории) -----
        st.divider()
        st.subheader("📋 Личные встречи (ручной ввод)")
        # Список команд для выбора – используем те, что есть в df_teams или только текущие две
        all_teams = []
        if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
            all_teams = st.session_state.df_teams['Команда'].tolist()
        else:
            all_teams = [home_name, away_name]
        
        with st.expander("➕ Добавить личную встречу"):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                manual_home = st.selectbox("Хозяева", all_teams, key="h2h_home")
            with col_b:
                manual_away = st.selectbox("Гости", all_teams, key="h2h_away")
            with col_c:
                manual_sets = st.text_input("Счёт по сетам", placeholder="3:1")
            manual_points = st.number_input("Фора по очкам (+, если хозяева выиграли)", step=0.5)
            manual_date = st.text_input("Дата", placeholder="01.01.2026")
            if st.button("Добавить"):
                key = (manual_home, manual_away)
                st.session_state.h2h_manual.setdefault(key, []).append({
                    'Дата': manual_date or "(дата не указана)",
                    'Хозяева': manual_home,
                    'Гости': manual_away,
                    'Счёт по сетам': manual_sets,
                    'Фора по очкам': manual_points
                })
                st.success("Добавлено")
                st.rerun()
        
        # Отображение истории для текущей пары
        key_pair = (home_name, away_name)
        reverse_key = (away_name, home_name)
        h2h_data = []
        for m in st.session_state.h2h_manual.get(key_pair, []):
            h2h_data.append(m)
        for m in st.session_state.h2h_manual.get(reverse_key, []):
            new_m = m.copy()
            new_m['Хозяева'] = home_name
            new_m['Гости'] = away_name
            new_m['Фора по очкам'] = -m['Фора по очкам']
            h2h_data.append(new_m)
        
        if h2h_data:
            df_h2h = pd.DataFrame(h2h_data)
            st.subheader(f"История встреч: {home_name} – {away_name}")
            st.dataframe(df_h2h[['Дата', 'Хозяева', 'Гости', 'Счёт по сетам', 'Фора по очкам']])
            if st.button("Очистить историю этой пары"):
                st.session_state.h2h_manual.pop(key_pair, None)
                st.session_state.h2h_manual.pop(reverse_key, None)
                st.rerun()
        else:
            st.info("Нет данных о личных встречах. Добавьте вручную выше.")
