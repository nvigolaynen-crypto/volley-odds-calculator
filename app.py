import streamlit as st
import pandas as pd
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# ------------------------------------------------------------
# Функции парсинга
# ------------------------------------------------------------
def get_parser_by_url(url: str):
    if "volley.ru" in url:
        return RussiaVolleyRuParser()
    elif "dataproject.com" in url:
        return DataProjectParser()
    else:
        return None

def load_teams(url, combine_phases):
    parser = get_parser_by_url(url)
    if parser is None:
        return None, "Неподдерживаемый URL. Используйте volley.ru или dataproject.com"
    df, error = parser.fetch_stats(url, combine_phases=combine_phases)
    if df is not None and not df.empty and 'Команда' in df.columns:
        return df, None
    else:
        return None, error or "Не удалось загрузить данные"

# ------------------------------------------------------------
# Настройки страницы
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
if 'url' not in st.session_state:
    st.session_state.url = ""
if 'combine_phases' not in st.session_state:
    st.session_state.combine_phases = False

# ------------------------------------------------------------
# Форма загрузки данных
# ------------------------------------------------------------
with st.form("load_form"):
    st.subheader("Ссылка на турнирную таблицу")
    url_input = st.text_input("URL", value=st.session_state.url, placeholder="https://volley.ru/... или https://...dataproject.com...")
    
    combine_phases = False
    if "dataproject.com" in url_input:
        combine_phases = st.checkbox("Складывать все этапы (только Data Project)", value=st.session_state.combine_phases)
    
    load_clicked = st.form_submit_button("📥 Загрузить данные")
    
    if load_clicked and url_input:
        with st.spinner("Загрузка..."):
            df, error = load_teams(url_input, combine_phases)
            if df is not None:
                st.session_state.df_teams = df
                st.session_state.url = url_input
                st.session_state.combine_phases = combine_phases
                st.success(f"Загружено {len(df)} команд")
                st.rerun()
            else:
                st.error(f"Ошибка: {error}")
                st.session_state.df_teams = None

# ------------------------------------------------------------
# Форма ввода команд и расчёта
# ------------------------------------------------------------
with st.form("predict_form"):
    st.subheader("Команды")
    
    manual_mode = st.checkbox("Ввести статистику вручную", value=st.session_state.manual_mode)
    if manual_mode != st.session_state.manual_mode:
        st.session_state.manual_mode = manual_mode
        st.rerun()
    
    col_home, col_away = st.columns(2)
    
    # ---- Домашняя команда ----
    with col_home:
        st.markdown("**ДОМАШНЯЯ КОМАНДА**")
        if manual_mode:
            home_name = st.text_input("Название", key="home_name")
            home_sets_v = st.number_input("Sets V", min_value=0, step=1, key="home_sets_v")
            home_sets_p = st.number_input("Sets P", min_value=0, step=1, key="home_sets_p")
            home_balls_v = st.number_input("Balls V", min_value=0, step=1, key="home_balls_v")
            home_balls_p = st.number_input("Balls P", min_value=0, step=1, key="home_balls_p")
            home_data_ok = bool(home_name)
        else:
            if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
                teams_list = st.session_state.df_teams['Команда'].tolist()
                home_name = st.selectbox("Название", teams_list, key="home_select")
                row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home_name].iloc[0]
                sets_v, sets_p = map(int, row['Сеты'].split(':'))
                balls_v, balls_p = map(int, row['Мячи'].split(':'))
                home_sets_v, home_sets_p = sets_v, sets_p
                home_balls_v, home_balls_p = balls_v, balls_p
                home_data_ok = True
                st.caption(f"Сеты: {sets_v}:{sets_p} | Мячи: {balls_v}:{balls_p}")
            else:
                st.warning("Сначала загрузите данные или включите ручной ввод.")
                home_name = ""
                home_sets_v = home_sets_p = home_balls_v = home_balls_p = 0
                home_data_ok = False
    
    # ---- Гостевая команда ----
    with col_away:
        st.markdown("**ГОСТЕВАЯ КОМАНДА**")
        if manual_mode:
            away_name = st.text_input("Название", key="away_name")
            away_sets_v = st.number_input("Sets V", min_value=0, step=1, key="away_sets_v")
            away_sets_p = st.number_input("Sets P", min_value=0, step=1, key="away_sets_p")
            away_balls_v = st.number_input("Balls V", min_value=0, step=1, key="away_balls_v")
            away_balls_p = st.number_input("Balls P", min_value=0, step=1, key="away_balls_p")
            away_data_ok = bool(away_name)
        else:
            if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
                teams_list = st.session_state.df_teams['Команда'].tolist()
                away_name = st.selectbox("Название", teams_list, key="away_select")
                row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away_name].iloc[0]
                sets_v, sets_p = map(int, row['Сеты'].split(':'))
                balls_v, balls_p = map(int, row['Мячи'].split(':'))
                away_sets_v, away_sets_p = sets_v, sets_p
                away_balls_v, away_balls_p = balls_v, balls_p
                away_data_ok = True
                st.caption(f"Сеты: {sets_v}:{sets_p} | Мячи: {balls_v}:{balls_p}")
            else:
                st.warning("Сначала загрузите данные или включите ручной ввод.")
                away_name = ""
                away_sets_v = away_sets_p = away_balls_v = away_balls_p = 0
                away_data_ok = False
    
    calc_clicked = st.form_submit_button("Рассчитать котировки", use_container_width=True)

# ------------------------------------------------------------
# Результаты расчёта
# ------------------------------------------------------------
if calc_clicked:
    if not home_data_ok or not away_data_ok:
        st.error("Заполните данные для обеих команд.")
    elif home_name == away_name:
        st.error("Выберите разные команды.")
    else:
        # Прогноз по сетам: определяем фаворита (независимо от того, хозяин или гость)
        st.subheader("📈 Прогноз по сетам")
        home_winrate = home_sets_v / (home_sets_v + home_sets_p) if (home_sets_v + home_sets_p) > 0 else 0.5
        away_winrate = away_sets_v / (away_sets_v + away_sets_p) if (away_sets_v + away_sets_p) > 0 else 0.5
        
        if home_winrate > away_winrate:
            favorite = home_name
            fav_winrate = home_winrate
            underdog = away_name
        else:
            favorite = away_name
            fav_winrate = away_winrate
            underdog = home_name
        
        margin = 0.05
        odds_fav = (1 - margin) / fav_winrate if fav_winrate > 0 else 0
        
        st.write(f"**Фаворит:** {favorite}")
        st.write(f"**Вероятность победы фаворита:** {fav_winrate:.1%}")
        st.write(f"**Коэффициент на победу {favorite} (с маржой 5%):** {odds_fav:.2f}")
        st.caption("Прогноз основан на проценте выигранных сетов. Коэффициент рассчитан с заложенной маржой букмекера 5%.")

        # Прогноз по очкам (фора) – относительно хозяев
        st.subheader("⚖️ Прогноз по очкам (фора)")
        total_matches = (home_sets_v + home_sets_p) // 3 if (home_sets_v + home_sets_p) > 0 else 30
        home_avg_diff = (home_balls_v - home_balls_p) / total_matches if total_matches > 0 else 0
        away_avg_diff = (away_balls_v - away_balls_p) / total_matches if total_matches > 0 else 0
        expected_diff = home_avg_diff - away_avg_diff
        handicap = round(expected_diff, 1)
        if handicap > 0:
            st.success(f"**Фора на матч:** {handicap} (в пользу хозяев)")
        elif handicap < 0:
            st.success(f"**Фора на матч:** {handicap} (в пользу гостей)")
        else:
            st.info("Фора близка к нулю – команды примерно равны")
        st.caption("Фора рассчитана как средняя разница очков за матч (хозяева − гости).")

        # ----- Личные встречи (ручной ввод) -----
        st.divider()
        st.subheader("📋 Личные встречи (ручной ввод)")
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
            if st.button("Добавить", key="add_h2h"):
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
