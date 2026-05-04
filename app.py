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

# Инициализация состояния
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None

if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}  # ключ (team1, team2) -> список матчей [{'Дата':, 'Хозяева':, 'Гости':, 'Счёт':}]

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
            # Расчёт прогноза
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
            st.subheader("📋 Личные встречи")

            # Ручной ввод личных встреч
            with st.expander("➕ Добавить личную встречу вручную"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    manual_home = st.selectbox("Хозяева (ручной ввод)", teams, key="manual_home")
                with col_b:
                    manual_away = st.selectbox("Гости (ручной ввод)", teams, key="manual_away")
                with col_c:
                    manual_score = st.text_input("Счёт (например, 3:1)", key="manual_score")
                manual_date = st.text_input("Дата (необязательно)", placeholder="01.01.2026", key="manual_date")
                if st.button("Добавить личную встречу"):
                    if manual_home and manual_away and manual_score and ":" in manual_score:
                        key = (manual_home, manual_away)
                        if key not in st.session_state.h2h_manual:
                            st.session_state.h2h_manual[key] = []
                        st.session_state.h2h_manual[key].append({
                            'Дата': manual_date if manual_date else "(ручной ввод)",
                            'Хозяева': manual_home,
                            'Гости': manual_away,
                            'Счёт': manual_score
                        })
                        st.success(f"Добавлен матч {manual_home} – {manual_away} {manual_score}")
                        st.rerun()
                    else:
                        st.error("Заполните хозяев, гостей и счёт в формате X:Y")

            # Отображение личных встреч
            key_pair = (home, away)
            reverse_key = (away, home)
            h2h_data = []
            # Сначала ручные данные
            if key_pair in st.session_state.h2h_manual:
                h2h_data.extend(st.session_state.h2h_manual[key_pair])
            if reverse_key in st.session_state.h2h_manual:
                # Если были добавлены в обратном порядке, нужно привести к стандартному виду при отображении?
                for m in st.session_state.h2h_manual[reverse_key]:
                    h2h_data.append({
                        'Дата': m['Дата'],
                        'Хозяева': m['Гости'],
                        'Гости': m['Хозяева'],
                        'Счёт': m['Счёт']
                    })
            # Затем парсинг с сайта (только для России)
            parser = get_parser(url)
            if "volley.ru" in url:
                try:
                    parsed_df = parser.fetch_head_to_head(url, home, away)
                    if not parsed_df.empty:
                        h2h_data.extend(parsed_df.to_dict('records'))
                except Exception as e:
                    st.warning(f"Не удалось загрузить данные с сайта: {e}")

            if h2h_data:
                df_h2h = pd.DataFrame(h2h_data)
                # Убираем дубликаты по всем колонкам (если ручные данные перекрываются с сайтом)
                df_h2h = df_h2h.drop_duplicates()
                st.subheader(f"История встреч: {home} – {away}")
                st.dataframe(df_h2h)
                # Кнопка очистки ручных данных для этой пары
                if st.button(f"Очистить ручные данные для {home} – {away}"):
                    if key_pair in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[key_pair]
                    if reverse_key in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[reverse_key]
                    st.rerun()
            else:
                st.info("Нет ни ручных, ни автоматических данных о личных встречах")
        else:
            st.info("Выберите две разные команды")
