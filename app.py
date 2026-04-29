import streamlit as st
import re
import pandas as pd
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Инициализируем состояние для хранения данных
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None

# Ввод URL
url = st.text_input("Введите URL страницы с результатами (шахматка / таблица)", 
                    "https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy")

# Автоматическое определение парсера
if url:
    if "volley.ru" in url:
        parser = RussiaVolleyRuParser()
        parser_name = "volley.ru"
    elif "dataproject.com" in url:
        parser = DataProjectParser()
        parser_name = "Data Project"
    else:
        parser = None
        parser_name = "неизвестный"
        st.warning("Ссылка не распознана. Поддерживаются volley.ru и dataproject.com")

if st.button("Парсить") and url:
    with st.spinner("Парсинг..."):
        try:
            if "volley.ru" in url:
                df, _ = parser.fetch_stats(url)
                st.session_state.df_teams = df
                st.session_state.parsed_data = df
                st.success("Данные успешно загружены")
            elif "dataproject.com" in url:
                # Для DataProject нужно извлечь fed и comp_id из URL
                # Пример: https://cbv-web.dataproject.com/CompetitionMatches.aspx?ID=18
                fed_match = re.search(r'https?://([a-z]+)-web\.dataproject\.com', url)
                comp_match = re.search(r'[?&]ID=(\d+)', url)
                if fed_match and comp_match:
                    fed = fed_match.group(1)
                    comp_id = comp_match.group(1)
                    df = parser.fetch_by_ids(fed, comp_id=comp_id)
                    st.session_state.df_teams = df
                    st.session_state.parsed_data = df
                    st.success("Данные Data Project загружены")
                else:
                    st.error("Не удалось извлечь fed и comp_id из URL. Убедитесь, что ссылка ведёт на страницу соревнования (например, .../CompetitionMatches.aspx?ID=18)")
            else:
                st.error("Парсер для этого сайта не реализован")
        except Exception as e:
            st.error(f"Ошибка: {e}")

# Отображение таблицы, если данные есть
if st.session_state.df_teams is not None:
    st.subheader("Турнирная таблица (сеты и мячи)")
    st.dataframe(st.session_state.df_teams)
    
    # Блок прогноза
    st.subheader("📊 Прогноз на матч")
    col1, col2 = st.columns(2)
    with col1:
        home_team = st.selectbox("Выберите домашнюю команду", st.session_state.df_teams['Команда'].tolist())
    with col2:
        away_team = st.selectbox("Выберите гостевую команду", st.session_state.df_teams['Команда'].tolist())
    
    if home_team and away_team and home_team != away_team:
        # Извлекаем статистику команд
        home_stats = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home_team].iloc[0]
        away_stats = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away_team].iloc[0]
        
        # Парсим сеты и мячи
        home_sets_won, home_sets_lost = map(int, home_stats['Сеты'].split(':'))
        away_sets_won, away_sets_lost = map(int, away_stats['Сеты'].split(':'))
        home_points_won, home_points_lost = map(int, home_stats['Мячи'].split(':'))
        away_points_won, away_points_lost = map(int, away_stats['Мячи'].split(':'))
        
        # Средняя разница очков за матч (фора)
        home_avg_diff = (home_points_won - home_points_lost) / 30  # примерно 30 матчей
        away_avg_diff = (away_points_won - away_points_lost) / 30
        
        # Прогноз форы (разница очков в матче) – упрощённая модель
        predicted_diff = home_avg_diff - away_avg_diff
        # Прогноз на сеты: просто сравниваем winrate сетов
        home_set_winrate = home_sets_won / (home_sets_won + home_sets_lost) if (home_sets_won + home_sets_lost) > 0 else 0.5
        away_set_winrate = away_sets_won / (away_sets_won + away_sets_lost) if (away_sets_won + away_sets_lost) > 0 else 0.5
        predicted_winner = home_team if home_set_winrate > away_set_winrate else away_team
        
        st.markdown("---")
        st.write(f"**Ожидаемая фора (разница очков) в матче:** {predicted_diff:+.1f} очков в пользу {'хозяев' if predicted_diff > 0 else 'гостей'}")
        st.write(f"**Прогноз на победителя по сетам:** {predicted_winner}")
        
        # Дополнительно: вероятность победы по сетам (простая логистическая)
        prob_home = 1 / (1 + (away_set_winrate / max(home_set_winrate, 0.01)))
        st.write(f"**Вероятность победы {home_team}:** {prob_home:.1%}")
        st.write("*(прогноз основан на средних показателях сезона, не учитывает текущую форму)*")
    else:
        st.info("Выберите две разные команды для прогноза")
