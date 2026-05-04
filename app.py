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
        raise ValueError("URL не поддерживается")

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
            st.session_state.df_teams = df
            st.success("Данные загружены")
        except Exception as e:
            st.error(f"Ошибка: {e}")

if st.session_state.df_teams is not None:
    teams = st.session_state.df_teams['Команда'].tolist()
    if not teams:
        st.warning("Нет команд для отображения")
    else:
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
            except:
                st.error("Ошибка формата данных")
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
            st.subheader("📋 Личные встречи")

            # Ручной ввод форы
            with st.expander("➕ Добавить личную встречу (фора по очкам)"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    h_home = st.selectbox("Хозяева", teams, key="manual_home")
                with col_b:
                    h_away = st.selectbox("Гости", teams, key="manual_away")
                with col_c:
                    h_handicap = st.number_input("Фора (очки)", step=0.5, format="%.1f", key="manual_handicap",
                                                 help="Положительное – победа хозяев, отрицательное – победа гостей")
                h_date = st.text_input("Дата (необязательно)", key="manual_date")
                if st.button("Добавить"):
                    if h_home and h_away and h_handicap is not None:
                        key = (h_home, h_away)
                        if key not in st.session_state.h2h_manual:
                            st.session_state.h2h_manual[key] = []
                        st.session_state.h2h_manual[key].append({
                            'Дата': h_date if h_date else "(ручной ввод)",
                            'Хозяева': h_home,
                            'Гости': h_away,
                            'Фора': h_handicap
                        })
                        st.success("Добавлено")
                        st.rerun()
                    else:
                        st.error("Заполните все поля")

            # Сбор всех встреч для пары home–away
            pair = (home, away)
            rev_pair = (away, home)
            h2h = []

            # Прямые ручные
            if pair in st.session_state.h2h_manual:
                for m in st.session_state.h2h_manual[pair]:
                    h2h.append({
                        'Дата': m['Дата'],
                        'Хозяева': m['Хозяева'],
                        'Гости': m['Гости'],
                        'Фора': f"{m['Фора']}" if m['Фора'] <= 0 else f"{m['Фора']}",
                        'Счёт': ''
                    })
            # Обратные ручные (привести к виду home vs away)
            if rev_pair in st.session_state.h2h_manual:
                for m in st.session_state.h2h_manual[rev_pair]:
                    new_h = -m['Фора']
                    h2h.append({
                        'Дата': m['Дата'],
                        'Хозяева': home,
                        'Гости': away,
                        'Фора': f"{new_h}" if new_h <= 0 else f"{new_h}",
                        'Счёт': ''
                    })

            # Автоматические с сайта (для России)
            if "volley.ru" in url:
                try:
                    parser = get_parser(url)
                    df_site = parser.fetch_head_to_head(url, home, away)
                    if not df_site.empty:
                        for _, row in df_site.iterrows():
                            h2h.append({
                                'Дата': row['Дата'],
                                'Хозяева': row['Хозяева'],
                                'Гости': row['Гости'],
                                'Счёт': row['Счёт'],
                                'Фора': ''
                            })
                except:
                    pass

            if h2h:
                df_h2h = pd.DataFrame(h2h).drop_duplicates()
                st.dataframe(df_h2h[['Дата', 'Хозяева', 'Гости', 'Счёт', 'Фора']].rename(columns={'Фора': 'Фора (очки)'}))
                if st.button("Очистить ручные данные для этой пары"):
                    if pair in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[pair]
                    if rev_pair in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[rev_pair]
                    st.rerun()
            else:
                st.info("Нет данных. Добавьте вручную выше.")
        else:
            st.info("Выберите две разные команды")
