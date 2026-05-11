import streamlit as st
import pandas as pd
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser
from parsers.italy import ItalyParser
from parsers.poland import PolandParser
from parsers.turkey import TurkeyParser

# ------------------------------------------------------------
# Функция определения парсера по URL
# ------------------------------------------------------------
def get_parser_by_url(url: str):
    if "volley.ru" in url:
        return RussiaVolleyRuParser()
    elif "dataproject.com" in url:
        return DataProjectParser()
    elif "legavolley.it" in url:
        return ItalyParser()
    elif "plusliga" in url or "poland" in url:
        return PolandParser()
    elif "turkey" in url or "tvf" in url:
        return TurkeyParser()
    else:
        return None

# ------------------------------------------------------------
# Настройка страницы
# ------------------------------------------------------------
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

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
        "https://www.legavolley.it/classifica/?IdCampionato=975"
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
# Ручной ввод с примером для Италии
# ------------------------------------------------------------
elif mode == "Ручной ввод команд":
    st.subheader("Введите данные команд вручную")
    st.markdown("Формат: `Название;Сеты;Мячи` (каждая команда с новой строки)")
    st.caption("Пример: `Abba Pineto;66:32;2273:2089`")

    italy_example = """Abba Pineto;66:32;2273:2089
Gruppo Consoli Sferc Brescia;66:36;2313:2159
Tinet Prata di Pordenone;62:32;2185:2000
Consar Ravenna;60:38;2283:2105
Virtus Aversa;55:46;2324:2227
Rinascita Lagonegro;45:59;2330:2271
Banca Macerata Fisiomed MC;60:49;2219:2212
Alva Inox 2 Emme Service Porto Viro;46:56;2257:2289
Prisma La Cascina Taranto;43:51;2098:2138
Romeo Sorrento;44:56;2215:2299
Sviluppo Sud Catania;44:60;2231:2337
Essence Hotels Fano;41:59;2155:2283
Emma Villas Codyeco Lupi Siena;39:63;2202:2347
Campi Reali Cantù;29:73;2072:2401"""

    teams_input = st.text_area("Введите команды", value=italy_example, height=300)

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("📋 Заполнить пример Италии"):
            st.session_state['italy_example'] = italy_example
            st.rerun()
    if 'italy_example' in st.session_state and teams_input != st.session_state.italy_example:
        teams_input = st.session_state.italy_example

    if st.button("Загрузить команды"):
        data = []
        for line in teams_input.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            parts = line.split(';')
            if len(parts) >= 3:
                team, sets, points = parts[0].strip(), parts[1].strip(), parts[2].strip()
                if ':' in sets and ':' in points:
                    data.append({'Команда': team, 'Сеты': sets, 'Мячи': points})
                else:
                    st.warning(f"Пропущена строка (неверный формат): {line}")
            else:
                st.warning(f"Пропущена строка (ожидается 3 части): {line}")
        if data:
            st.session_state.df_teams = pd.DataFrame(data)
            st.success(f"Загружено {len(data)} команд")
        else:
            st.error("Не удалось распознать данные. Проверьте формат.")

# ------------------------------------------------------------
# Отображение прогноза (общая логика)
# ------------------------------------------------------------
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
            handicap = round(home_avg_diff - away_avg_diff, 1)

            if handicap > 0:
                st.success(f"Фора на матч: **{handicap}** (в пользу хозяев)")
            elif handicap < 0:
                st.success(f"Фора на матч: **{handicap}** (в пользу гостей)")
            else:
                st.info("Фора близка к нулю – команды примерно равны")

            home_winrate = home_sets_w / (home_sets_w + home_sets_l) if (home_sets_w + home_sets_l) > 0 else 0.5
            away_winrate = away_sets_w / (away_sets_w + away_sets_l) if (away_sets_w + away_sets_l) > 0 else 0.5
            predicted_winner = home if home_winrate > away_winrate else away
            prob_home = 1 / (1 + (away_winrate / max(home_winrate, 0.01)))

            st.write(f"**Прогноз победителя по сётам:** {predicted_winner}")
            st.write(f"**Вероятность победы {home}:** {prob_home:.1%}")
            st.caption("Прогноз основан на статистике сезона")

            # ----- Ручной ввод личных встреч -----
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

            # Отображение истории
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
    if st.session_state.df_teams is not None and st.session_state.df_teams.empty:
        st.warning("Таблица команд пуста. Проверьте ввод.")
    else:
        st.info("Выберите режим и загрузите данные.")
