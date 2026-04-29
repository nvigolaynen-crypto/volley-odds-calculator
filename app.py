import streamlit as st
import pandas as pd
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

def get_parser(url: str):
    if "volley.ru" in url:
        return RussiaVolleyRuParser()
    elif "dataproject.com" in url:
        return DataProjectParser()
    else:
        raise ValueError("URL не поддерживается. Используйте volley.ru или dataproject.com")

st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None

# Ввод URL
url = st.text_input(
    "Введите URL страницы с результатами (таблица, standings)",
    "https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy"
)

# Чекбокс "Считать все этапы" (только для volley.ru)
combine_phases = st.checkbox("Считать все этапы (предварительный + плей-офф)", value=False)

if st.button("Парсить") and url:
    with st.spinner("Загрузка данных..."):
        try:
            parser = get_parser(url)
            df, _ = parser.fetch_stats(url, combine_phases=combine_phases)
            st.session_state.df_teams = df
            st.success("Данные загружены")
        except Exception as e:
            st.error(f"Ошибка: {e}")

if st.session_state.df_teams is not None:
    # Без вывода полной таблицы – только выбор команд
    st.divider()
    st.subheader("📊 Прогноз на матч")

    # Получаем список команд
    teams = st.session_state.df_teams['Команда'].tolist()

    col1, col2 = st.columns(2)
    with col1:
        home = st.selectbox("Домашняя команда", teams)
        # Показываем статистику выбранной команды
        home_data = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
        st.caption(f"Сеты: {home_data['Сеты']} | Мячи: {home_data['Мячи']}")

    with col2:
        away = st.selectbox("Гостевая команда", teams)
        away_data = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
        st.caption(f"Сеты: {away_data['Сеты']} | Мячи: {away_data['Мячи']}")

    if home and away and home != away:
        home_stats = home_data
        away_stats = away_data

        try:
            home_sets_w, home_sets_l = map(int, home_stats['Сеты'].split(':'))
            away_sets_w, away_sets_l = map(int, away_stats['Сеты'].split(':'))
            home_pts_w, home_pts_l = map(int, home_stats['Мячи'].split(':'))
            away_pts_w, away_pts_l = map(int, away_stats['Мячи'].split(':'))
        except:
            st.error("Ошибка формата данных")
            st.stop()

        # Количество матчей: для России при объединении этапов может быть больше 30,
        # но для простоты оставим 30 (можно вычислить по сумме побед+поражений)
        # Лучше использовать фактическое количество матчей, чтобы фора была адекватной
        total_matches = (home_sets_w + home_sets_l) // 3  # примерно
        if total_matches == 0:
            total_matches = 30

        home_avg_diff = (home_pts_w - home_pts_l) / total_matches
        away_avg_diff = (away_pts_w - away_pts_l) / total_matches
        expected_diff = home_avg_diff - away_avg_diff
        handicap = round(expected_diff, 1)

        if handicap > 0:
            st.success(f"Фора на матч: **{handicap}** (в пользу хозяев)")
        elif handicap < 0:
            st.success(f"Фора на матч: **{handicap}** (в пользу гостей)")

        home_winrate = home_sets_w / (home_sets_w + home_sets_l) if (home_sets_w + home_sets_l) > 0 else 0.5
        away_winrate = away_sets_w / (away_sets_w + away_sets_l) if (away_sets_w + away_sets_l) > 0 else 0.5
        predicted_winner = home if home_winrate > away_winrate else away
        prob_home = 1 / (1 + (away_winrate / max(home_winrate, 0.01)))

        st.write(f"**Прогноз победителя по сётам:** {predicted_winner}")
        st.write(f"**Вероятность победы {home}:** {prob_home:.1%}")
        st.caption("Прогноз основан на статистике сезона (может отличаться)")
    else:
        st.info("Выберите две разные команды")
