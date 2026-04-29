import streamlit as st
import pandas as pd
from parsers.russia_volleyru import RussiaVolleyRuParser

st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика и прогнозы")

# Инициализация состояния
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None

# Ввод URL
url = st.text_input("Введите URL страницы с результатами (список матчей)", 
                    "https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy")

if st.button("Парсить") and url:
    parser = RussiaVolleyRuParser()
    with st.spinner("Загрузка данных..."):
        try:
            df, _ = parser.fetch_stats(url)
            st.session_state.df_teams = df
            st.success("Данные успешно загружены")
        except Exception as e:
            st.error(f"Ошибка: {e}")

# Отображение таблицы
if st.session_state.df_teams is not None:
    st.subheader("Турнирная таблица (сеты и мячи)")
    st.dataframe(st.session_state.df_teams)
    
    # Блок прогноза
    st.divider()
    st.subheader("📊 Прогноз на матч с учётом форы")
    
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Выберите домашнюю команду", st.session_state.df_teams['Команда'].tolist())
    with col2:
        away_team = st.selectbox("Выберите гостевую команду", st.session_state.df_teams['Команда'].tolist())
    
    if home_team and away_team and home_team != away_team:
        # Получаем статистику команд
        home_stats = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home_team].iloc[0]
        away_stats = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away_team].iloc[0]
        
        # Парсим разницу очков
        home_points_won, home_points_lost = map(int, home_stats['Мячи'].split(':'))
        away_points_won, away_points_lost = map(int, away_stats['Мячи'].split(':'))
        
        # Средняя разница очков за матч (всего 30 туров)
        home_avg_diff = (home_points_won - home_points_lost) / 30
        away_avg_diff = (away_points_won - away_points_lost) / 30
        
        # Расчёт форы (ожидаемая разница в пользу хозяев)
        expected_diff = home_avg_diff - away_avg_diff
        # Формируем фору для гандикапа
        if expected_diff > 0:
            handicap = f"{expected_diff:.1f}"
        else:
            handicap = f"{expected_diff:.1f}"
        
        st.info(f"**Ожидаемая фора на матч:** {handicap}")
        if expected_diff > 0:
            st.success(f"✅ {home_team} является фаворитом. Фора для хозяев: +{handicap} очков.")
        else:
            st.success(f"✅ {away_team} является фаворитом. Фора для гостей: {handicap} очков.")
        
        # Прогноз победителя по сетам
        home_sets_won, home_sets_lost = map(int, home_stats['Сеты'].split(':'))
        away_sets_won, away_sets_lost = map(int, away_stats['Сеты'].split(':'))
        home_set_winrate = home_sets_won / (home_sets_won + home_sets_lost) if (home_sets_won + home_sets_lost) > 0 else 0.5
        away_set_winrate = away_sets_won / (away_sets_won + away_sets_lost) if (away_sets_won + away_sets_lost) > 0 else 0.5
        predicted_winner = home_team if home_set_winrate > away_set_winrate else away_team
        prob_home = 1 / (1 + max(away_set_winrate, 0.01) / max(home_set_winrate, 0.01))
        
        st.markdown("---")
        st.write(f"**Прогноз исхода матча:** {predicted_winner}")
        st.write(f"**Вероятность победы {home_team}:** {prob_home:.1%}")
        st.caption("Прогнозы основаны на средней статистике сезона и могут отличаться от реального результата.")
    else:
        st.info("Выберите две разные команды для отображения прогноза")
