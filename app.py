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
# Настройка страницы
# ------------------------------------------------------------
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Инициализация состояния
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None
if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}

# ------------------------------------------------------------
# Режимы работы
# ------------------------------------------------------------
mode = st.radio("Выберите режим", ["Автоматический парсинг (по URL)", "Ручной ввод команд"], horizontal=True)

# ------------------------------------------------------------
# Автоматический парсинг
# ------------------------------------------------------------
if mode == "Автоматический парсинг (по URL)":
    url = st.text_input(
        "Введите URL страницы с результатами",
        "https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy"
    )
    combine_phases = False
    if "dataproject.com" in url:
        combine_phases = st.checkbox("складывать все этапы (только для Data Project)", value=False)

    if st.button("Парсить") and url:
        parser = get_parser_by_url(url)
        if parser is None:
            st.error("Автоматический парсинг для этого сайта не поддерживается. Переключитесь на ручной ввод.")
        else:
            with st.spinner("Загрузка данных..."):
                try:
                    df, error = parser.fetch_stats(url, combine_phases=combine_phases)
                    if df is not None and not df.empty and 'Команда' in df.columns:
                        st.session_state.df_teams = df
                        st.success(f"Данные загружены. Команд: {len(df)}")
                    else:
                        st.warning(f"Не удалось загрузить таблицу: {error or 'неизвестная ошибка'}. Попробуйте ручной ввод.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# ------------------------------------------------------------
# Ручной ввод команд
# ------------------------------------------------------------
elif mode == "Ручной ввод команд":
    st.subheader("Добавление команды вручную")
    with st.form(key="add_team_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            team_name = st.text_input("Название команды")
        with col2:
            sets_won = st.number_input("Выигранные сеты", min_value=0, step=1, value=0)
            pts_won = st.number_input("Выигранные очки", min_value=0, step=1, value=0)
        with col3:
            sets_lost = st.number_input("Проигранные сеты", min_value=0, step=1, value=0)
            pts_lost = st.number_input("Проигранные очки", min_value=0, step=1, value=0)
        submitted = st.form_submit_button("➕ Добавить команду")
        if submitted and team_name:
            if st.session_state.df_teams is not None and team_name in st.session_state.df_teams['Команда'].values:
                st.warning("Такая команда уже есть")
            else:
                new_row = pd.DataFrame({
                    'Команда': [team_name],
                    'Сеты': [f"{sets_won}:{sets_lost}"],
                    'Мячи': [f"{pts_won}:{pts_lost}"]
                })
                if st.session_state.df_teams is None:
                    st.session_state.df_teams = new_row
                else:
                    st.session_state.df_teams = pd.concat([st.session_state.df_teams, new_row], ignore_index=True)
                st.success(f"Команда {team_name} добавлена")
                st.rerun()

    if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
        st.subheader("Текущие команды")
        st.dataframe(st.session_state.df_teams[['Команда', 'Сеты', 'Мячи']], use_container_width=True)
        st.subheader("Удалить команду")
        team_to_delete = st.selectbox("Выберите команду для удаления", st.session_state.df_teams['Команда'].tolist())
        if st.button("🗑 Удалить выбранную команду"):
            st.session_state.df_teams = st.session_state.df_teams[st.session_state.df_teams['Команда'] != team_to_delete].reset_index(drop=True)
            st.rerun()
    else:
        st.info("Нет добавленных команд. Используйте форму выше.")

# ------------------------------------------------------------
# Прогноз
# ------------------------------------------------------------
if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
    if 'Команда' not in st.session_state.df_teams.columns:
        st.error("Некорректный формат данных: отсутствует колонка 'Команда'")
    else:
        teams = st.session_state.df_teams['Команда'].tolist()
        st.divider()
        st.subheader("⚙️ Настройки прогноза")
        predict_method = st.radio(
            "Прогноз на основе:",
            ["По сетам (победа/поражение)", "По очкам (разница очков за матч)"],
            horizontal=True
        )
        st.subheader("📊 Прогноз на матч")
        col1, col2 = st.columns(2)
        with col1:
            home = st.selectbox("Домашняя команда", teams, key="home_team")
            home_data = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
            st.caption(f"Сеты: {home_data['Сеты']} | Мячи: {home_data['Мячи']}")
        with col2:
            away = st.selectbox("Гостевая команда", teams, key="away_team")
            away_data = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
            st.caption(f"Сеты: {away_data['Сеты']} | Мячи: {away_data['Мячи']}")

        if home and away and home != away:
            try:
                home_sets_w, home_sets_l = map(int, home_data['Сеты'].split(':'))
                away_sets_w, away_sets_l = map(int, away_data['Сеты'].split(':'))
                home_pts_w, home_pts_l = map(int, home_data['Мячи'].split(':'))
                away_pts_w, away_pts_l = map(int, away_data['Мячи'].split(':'))
            except Exception as e:
                st.error(f"Ошибка формата данных: {e}")
                st.stop()

            if predict_method == "По сетам (победа/поражение)":
                home_winrate = home_sets_w / (home_sets_w + home_sets_l) if (home_sets_w + home_sets_l) > 0 else 0.5
                away_winrate = away_sets_w / (away_sets_w + away_sets_l) if (away_sets_w + away_sets_l) > 0 else 0.5
                predicted_winner = home if home_winrate > away_winrate else away
                prob_home = home_winrate
                margin = 0.05
                odds_home = (1 - margin) / prob_home if prob_home > 0 else 0
                st.write(f"**Прогноз победителя по сётам:** {predicted_winner}")
                st.write(f"**Вероятность победы {home}:** {prob_home:.1%}")
                st.write(f"**Коэффициент на победу {home} (с маржой 5%):** {odds_home:.2f}")
                st.caption("Прогноз основан на проценте выигранных сетов. Коэффициент рассчитан с заложенной маржой букмекера 5%.")
            else:  # по очкам
                total_matches = (home_sets_w + home_sets_l) // 3 if (home_sets_w + home_sets_l) > 0 else 30
                home_avg_diff = (home_pts_w - home_pts_l) / total_matches
                away_avg_diff = (away_pts_w - away_pts_l) / total_matches
                expected_diff = home_avg_diff - away_avg_diff
                handicap = round(expected_diff, 1)
                if handicap > 0:
                    st.success(f"Фора на матч: **{handicap}** (в пользу хозяев)")
                elif handicap < 0:
                    st.success(f"Фора на матч: **{handicap}** (в пользу гостей)")
                else:
                    st.info("Фора близка к нулю – команды примерно равны")
                st.caption("Прогноз основан на разнице очков за матч (средняя фора).")

            # ----- Личные встречи -----
            st.divider()
            st.subheader("📋 Личные встречи (ручной ввод)")
            with st.expander("➕ Добавить личную встречу"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    manual_home = st.selectbox("Хозяева", teams, key="h2h_home")
                with col_b:
                    manual_away = st.selectbox("Гости", teams, key="h2h_away")
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

            key_pair = (home, away)
            reverse_key = (away, home)
            h2h_data = []
            for m in st.session_state.h2h_manual.get(key_pair, []):
                h2h_data.append(m)
            for m in st.session_state.h2h_manual.get(reverse_key, []):
                new_m = m.copy()
                new_m['Хозяева'] = home
                new_m['Гости'] = away
                new_m['Фора по очкам'] = -m['Фора по очкам']
                h2h_data.append(new_m)

            if h2h_data:
                df_h2h = pd.DataFrame(h2h_data)
                st.subheader(f"История встреч: {home} – {away}")
                st.dataframe(df_h2h[['Дата', 'Хозяева', 'Гости', 'Счёт по сетам', 'Фора по очкам']])
                if st.button("Очистить историю этой пары"):
                    st.session_state.h2h_manual.pop(key_pair, None)
                    st.session_state.h2h_manual.pop(reverse_key, None)
                    st.rerun()
            else:
                st.info("Нет данных о личных встречах. Добавьте вручную выше.")
        else:
            st.info("Выберите две разные команды")
else:
    st.info("Нет загруженных команд. Используйте автоматический парсинг (введите URL) или ручной ввод.")
