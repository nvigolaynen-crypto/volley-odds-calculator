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

if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}

url = st.text_input(
    "Введите URL страницы с результатами (таблица, standings)",
    "https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy"
)

combine_phases = st.checkbox("складывать все этапы (только для Data Project)", value=False)

if st.button("Парсить") and url:
    with st.spinner("Загрузка данных..."):
        try:
            parser = get_parser(url)
            df, _ = parser.fetch_stats(url, combine_phases=combine_phases)
            if df is not None and not df.empty and 'Команда' in df.columns:
                st.session_state.df_teams = df
                st.success("Данные загружены")
            else:
                st.warning("Не удалось загрузить данные. Возможно, турнир не найден или volleystats не дал результата.")
        except Exception as e:
            st.error(f"Ошибка: {e}")

if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
    if 'Команда' not in st.session_state.df_teams.columns:
        st.error("Некорректный формат данных: отсутствует колонка 'Команда'")
    else:
        teams = st.session_state.df_teams['Команда'].tolist()
        st.divider()
        st.subheader("📊 Прогноз на матч")

        col1, col2 = st.columns(2)
        with col1:
            home = st.selectbox("Домашняя команда", teams)
            home_data = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
            st.caption(f"Сеты: {home_data['Сеты']} | Мячи: {home_data['Мячи']}")
        with col2:
            away = st.selectbox("Гостевая команда", teams)
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

            total_matches = (home_sets_w + home_sets_l) // 3 if (home_sets_w + home_sets_l) > 0 else 30
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

            st.divider()
            st.subheader("📋 Личные встречи (ручной ввод)")

            with st.expander("➕ Добавить личную встречу вручную"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    manual_home = st.selectbox("Хозяева", teams, key="manual_home")
                with col_b:
                    manual_away = st.selectbox("Гости", teams, key="manual_away")
                with col_c:
                    manual_sets = st.text_input("Счёт по сетам (например, 3:1)", key="manual_sets", placeholder="3:1")
                manual_points = st.number_input("Фора по очкам (положительное – победа хозяев, отрицательное – победа гостей)", step=0.5, format="%.1f", key="manual_points")
                manual_date = st.text_input("Дата (необязательно)", placeholder="01.01.2026", key="manual_date")
                if st.button("Добавить личную встречу"):
                    if manual_home and manual_away and manual_points is not None:
                        key = (manual_home, manual_away)
                        if key not in st.session_state.h2h_manual:
                            st.session_state.h2h_manual[key] = []
                        st.session_state.h2h_manual[key].append({
                            'Дата': manual_date if manual_date else "(ручной ввод)",
                            'Хозяева': manual_home,
                            'Гости': manual_away,
                            'Счёт по сетам': manual_sets,
                            'Фора по очкам': manual_points
                        })
                        st.success(f"Добавлен матч {manual_home} – {manual_away}")
                        st.rerun()
                    else:
                        st.error("Заполните хозяев, гостей и фору по очкам")

            key_pair = (home, away)
            reverse_key = (away, home)
            h2h_data = []

            if key_pair in st.session_state.h2h_manual:
                for m in st.session_state.h2h_manual[key_pair]:
                    h2h_data.append({
                        'Дата': m['Дата'],
                        'Хозяева': m['Хозяева'],
                        'Гости': m['Гости'],
                        'Счёт по сетам': m.get('Счёт по сетам', ''),
                        'Фора по очкам': m['Фора по очкам']
                    })
            if reverse_key in st.session_state.h2h_manual:
                for m in st.session_state.h2h_manual[reverse_key]:
                    new_points = -m['Фора по очкам']
                    h2h_data.append({
                        'Дата': m['Дата'],
                        'Хозяева': home,
                        'Гости': away,
                        'Счёт по сетам': m.get('Счёт по сетам', ''),
                        'Фора по очкам': new_points
                    })

            if h2h_data:
                df_h2h = pd.DataFrame(h2h_data)
                df_h2h = df_h2h.drop_duplicates(subset=['Дата', 'Хозяева', 'Гости'])
                st.subheader(f"История встреч: {home} – {away}")
                df_h2h['Фора'] = df_h2h['Фора по очкам'].apply(lambda x: f"{x}" if x <= 0 else f"{x}")
                cols_to_show = ['Дата', 'Хозяева', 'Гости']
                if df_h2h['Счёт по сетам'].any():
                    cols_to_show.append('Счёт по сетам')
                cols_to_show.append('Фора')
                st.dataframe(df_h2h[cols_to_show].rename(columns={'Фора': 'Фора (очки)'}))
                if st.button(f"Очистить ручные данные для {home} – {away}"):
                    if key_pair in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[key_pair]
                    if reverse_key in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[reverse_key]
                    st.rerun()
            else:
                st.info("Нет данных о личных встречах. Добавьте вручную через раздел выше.")
        else:
            st.info("Выберите две разные команды")
elif st.session_state.df_teams is not None and st.session_state.df_teams.empty:
    st.warning("Таблица с командами пуста. Проверьте правильность URL и наличие данных.")
