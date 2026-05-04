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

# Хранилище ручных личных встреч
# Структура: {(команда1, команда2): [{'Дата': '...', 'Хозяева': '...', 'Гости': '...', 'Счёт': '...', 'Фора': число}]}
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
            st.subheader("📋 Личные встречи (только ручной ввод)")

            # Форма для добавления личной встречи
            with st.expander("➕ Добавить личную встречу"):
                col_a, col_b = st.columns(2)
                with col_a:
                    manual_home = st.selectbox("Хозяева", teams, key="manual_home")
                with col_b:
                    manual_away = st.selectbox("Гости", teams, key="manual_away")
                
                # Два варианта ввода: по сётам или по очкам
                input_type = st.radio("Тип результата", ["Счёт по сетам (3:1)", "Фора по очкам (5 или -5)"], horizontal=True)
                
                if input_type == "Счёт по сетам (3:1)":
                    manual_score = st.text_input("Счёт (например, 3:1)", key="manual_score")
                    if st.button("Добавить по счёту"):
                        if manual_home and manual_away and ":" in manual_score:
                            key = (manual_home, manual_away)
                            if key not in st.session_state.h2h_manual:
                                st.session_state.h2h_manual[key] = []
                            st.session_state.h2h_manual[key].append({
                                'Дата': "(ручной ввод)",
                                'Хозяева': manual_home,
                                'Гости': manual_away,
                                'Счёт': manual_score,
                                'Фора': ''
                            })
                            st.success(f"Добавлен матч {manual_home} – {manual_away} {manual_score}")
                            st.rerun()
                        else:
                            st.error("Введите счёт в формате X:Y")
                else:  # Фора по очкам
                    manual_handicap = st.number_input("Фора (очки)", step=0.5, format="%.1f", key="manual_handicap",
                                                      help="Положительное – победа хозяев, отрицательное – победа гостей")
                    if st.button("Добавить по форе"):
                        if manual_home and manual_away and manual_handicap is not None:
                            key = (manual_home, manual_away)
                            if key not in st.session_state.h2h_manual:
                                st.session_state.h2h_manual[key] = []
                            st.session_state.h2h_manual[key].append({
                                'Дата': "(ручной ввод)",
                                'Хозяева': manual_home,
                                'Гости': manual_away,
                                'Счёт': '',
                                'Фора': manual_handicap
                            })
                            st.success(f"Добавлен матч {manual_home} – {manual_away} с форой {manual_handicap}")
                            st.rerun()
                        else:
                            st.error("Заполните хозяев, гостей и фору")

            # Отображение личных встреч для выбранной пары
            key_pair = (home, away)
            reverse_key = (away, home)
            h2h_data = []

            # Добавляем ручные данные в прямом и обратном порядке (приводим к виду home vs away)
            if key_pair in st.session_state.h2h_manual:
                for m in st.session_state.h2h_manual[key_pair]:
                    h2h_data.append({
                        'Дата': m['Дата'],
                        'Хозяева': m['Хозяева'],
                        'Гости': m['Гости'],
                        'Счёт': m['Счёт'],
                        'Фора': m['Фора']
                    })
            if reverse_key in st.session_state.h2h_manual:
                for m in st.session_state.h2h_manual[reverse_key]:
                    # Если есть фора, меняем знак
                    new_handicap = -m['Фора'] if m['Фора'] != '' else ''
                    h2h_data.append({
                        'Дата': m['Дата'],
                        'Хозяева': home,
                        'Гости': away,
                        'Счёт': m['Счёт'],
                        'Фора': new_handicap
                    })

            if h2h_data:
                df_h2h = pd.DataFrame(h2h_data)
                df_h2h = df_h2h.drop_duplicates(subset=['Дата', 'Хозяева', 'Гости', 'Счёт', 'Фора'])
                st.subheader(f"История встреч: {home} – {away}")
                
                # Форматируем колонку Форы: для положительных чисел убираем знак +
                def format_handicap(val):
                    if isinstance(val, (int, float)) and val > 0:
                        return str(val)
                    elif isinstance(val, (int, float)) and val <= 0:
                        return str(val)
                    return str(val)
                
                if 'Фора' in df_h2h.columns:
                    df_h2h['Фора (очки)'] = df_h2h['Фора'].apply(lambda x: format_handicap(x) if x != '' else '')
                    cols = ['Дата', 'Хозяева', 'Гости']
                    if any(df_h2h['Счёт'] != ''):
                        cols.append('Счёт')
                    if any(df_h2h['Фора (очки)'] != ''):
                        cols.append('Фора (очки)')
                    st.dataframe(df_h2h[cols])
                else:
                    st.dataframe(df_h2h[['Дата', 'Хозяева', 'Гости', 'Счёт']])
                
                if st.button(f"🗑 Очистить все ручные данные для {home} – {away}"):
                    if key_pair in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[key_pair]
                    if reverse_key in st.session_state.h2h_manual:
                        del st.session_state.h2h_manual[reverse_key]
                    st.rerun()
            else:
                st.info("Нет ручных данных о личных встречах. Добавьте через раздел выше.")
        else:
            st.info("Выберите две разные команды")
