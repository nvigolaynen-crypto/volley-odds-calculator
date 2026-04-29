import streamlit as st
import pandas as pd
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# Словарь доступных парсеров
PARSERS = {
    "Россия (volley.ru)": RussiaVolleyRuParser(),
    "Data Project (универсальный)": DataProjectParser(),
}

st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Выбор парсера
parser_name = st.selectbox("Выберите источник данных", list(PARSERS.keys()))
parser = PARSERS[parser_name]

# Поле для URL
url = st.text_input("Введите URL страницы с результатами", 
                    "https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy")

if st.button("Парсить") and url:
    with st.spinner("Загрузка данных..."):
        try:
            df, _ = parser.fetch_stats(url)
            st.session_state.df_teams = df
            st.success("Данные загружены")
        except Exception as e:
            st.error(f"Ошибка: {e}")

# Инициализация состояния, если ещё нет
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None

if st.session_state.df_teams is not None:
    st.subheader("Турнирная таблица (сеты и мячи)")
    st.dataframe(st.session_state.df_teams)

    st.divider()
    st.subheader("📊 Прогноз на матч")

    col1, col2 = st.columns(2)
    with col1:
        home = st.selectbox("Домашняя команда", st.session_state.df_teams['Команда'].tolist())
    with col2:
        away = st.selectbox("Гостевая команда", st.session_state.df_teams['Команда'].tolist())

    if home and away and home != away:
        home_stats = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
        away_stats = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]

        # Извлекаем сеты и мячи
        try:
            home_sets_w, home_sets_l = map(int, home_stats['Сеты'].split(':'))
            away_sets_w, away_sets_l = map(int, away_stats['Сеты'].split(':'))
            home_pts_w, home_pts_l = map(int, home_stats['Мячи'].split(':'))
            away_pts_w, away_pts_l = map(int, away_stats['Мячи'].split(':'))
        except:
            st.error("Не удалось распарсить данные для прогноза")
            st.stop()

        # Средняя разница очков за матч
        total_matches = 30  # примерно
        home_avg_diff = (home_pts_w - home_pts_l) / total_matches
        away_avg_diff = (away_pts_w - away_pts_l) / total_matches
        expected_diff = home_avg_diff - away_avg_diff
        handicap = round(expected_diff, 1)

        if handicap > 0:
            st.success(f"Фора на матч: **{handicap}** (в пользу хозяев)")
        elif handicap < 0:
            st.success(f"Фора на матч: **{handicap}** (в пользу гостей)")

        # Прогноз по сётам
        home_winrate = home_sets_w / (home_sets_w + home_sets_l) if (home_sets_w + home_sets_l) > 0 else 0.5
        away_winrate = away_sets_w / (away_sets_w + away_sets_l) if (away_sets_w + away_sets_l) > 0 else 0.5
        predicted_winner = home if home_winrate > away_winrate else away
        prob_home = 1 / (1 + (away_winrate / max(home_winrate, 0.01)))

        st.write(f"**Прогноз победителя по сётам:** {predicted_winner}")
        st.write(f"**Вероятность победы {home}:** {prob_home:.1%}")
        st.caption("Прогноз основан на статистике сезона (может отличаться)")
    else:
        st.info("Выберите две разные команды")
