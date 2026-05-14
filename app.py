import streamlit as st
import pandas as pd
import re
import math
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# ------------------------------------------------------------
# Универсальный парсер таблиц (CSV, Excel, текст)
# ------------------------------------------------------------
def parse_table_to_df(data_source, file_type=None):
    if file_type == 'csv':
        content = data_source.getvalue().decode('utf-8')
        lines = content.splitlines()
        data = []
        number_pattern = r'[\d]+(?:[.,]\d+)?'  # числа: целые или с точкой/запятой
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Ищем строки, начинающиеся с цифры и пробела (номера команд)
            if re.match(r'^\d+\s+', line):
                numbers = re.findall(number_pattern, line)
                if len(numbers) < 4:
                    continue
                # Сеты (первые два числа)
                try:
                    sets_won = int(float(numbers[0].replace(',', '.')))
                    sets_lost = int(float(numbers[1].replace(',', '.')))
                except:
                    continue
                # Очки (убираем точки/запятые как разделители тысяч)
                pts_won_str = numbers[2].replace('.', '').replace(',', '')
                pts_lost_str = numbers[3].replace('.', '').replace(',', '')
                try:
                    pts_won = int(pts_won_str)
                    pts_lost = int(pts_lost_str)
                except:
                    continue
                # Название команды: всё между номером и первым числом
                without_number = re.sub(r'^\d+\s+', '', line)
                first_num_match = re.search(number_pattern, without_number)
                if first_num_match:
                    team = without_number[:first_num_match.start()].strip()
                else:
                    team = without_number.strip()
                # Удаляем возможные запятые в конце названия
                team = re.sub(r'[,;]\s*$', '', team).strip()
                if team:
                    data.append({
                        'Команда': team,
                        'Сеты': f"{sets_won}:{sets_lost}",
                        'Мячи': f"{pts_won}:{pts_lost}"
                    })
        if data:
            return pd.DataFrame(data)
        # fallback: стандартный pandas
        try:
            df = pd.read_csv(data_source, sep=None, engine='python', encoding='utf-8')
            # Поиск колонок по ключевым словам (как раньше)
            team_col, sets_won_col, sets_lost_col, pts_won_col, pts_lost_col = None, None, None, None, None
            for col in df.columns:
                col_low = str(col).lower()
                if 'squadra' in col_low or 'team' in col_low or 'nome' in col_low:
                    team_col = col
                if 'vinti' in col_low and 'set' in col_low:
                    sets_won_col = col
                if 'persi' in col_low and 'set' in col_low:
                    sets_lost_col = col
                if 'fatti' in col_low or ('punti' in col_low and 'fat' in col_low):
                    pts_won_col = col
                if 'subiti' in col_low or ('punti' in col_low and 'sub' in col_low):
                    pts_lost_col = col
            if team_col and sets_won_col and sets_lost_col and pts_won_col and pts_lost_col:
                rows = []
                for _, row in df.iterrows():
                    team = str(row[team_col]).strip()
                    if not team or team == 'nan':
                        continue
                    try:
                        sets_w = int(float(str(row[sets_won_col]).replace(',', '.')))
                        sets_l = int(float(str(row[sets_lost_col]).replace(',', '.')))
                        pts_w = int(float(str(row[pts_won_col]).replace('.', '').replace(',', '.')))
                        pts_l = int(float(str(row[pts_lost_col]).replace('.', '').replace(',', '.')))
                        rows.append({'Команда': team, 'Сеты': f"{sets_w}:{sets_l}", 'Мячи': f"{pts_w}:{pts_l}"})
                    except:
                        continue
                if rows:
                    return pd.DataFrame(rows)
        except Exception as e:
            pass
        return None
    elif file_type == 'xlsx':
        df_raw = pd.read_excel(data_source)
        # Аналогичный поиск колонок (как в предыдущей версии)
        team_col = sets_won_col = sets_lost_col = pts_won_col = pts_lost_col = None
        for col in df_raw.columns:
            col_low = str(col).lower()
            if 'squadra' in col_low or 'team' in col_low or 'nome' in col_low:
                team_col = col
            if 'vinti' in col_low and 'set' in col_low:
                sets_won_col = col
            if 'persi' in col_low and 'set' in col_low:
                sets_lost_col = col
            if 'fatti' in col_low or ('punti' in col_low and 'fat' in col_low):
                pts_won_col = col
            if 'subiti' in col_low or ('punti' in col_low and 'sub' in col_low):
                pts_lost_col = col
        if team_col and sets_won_col and sets_lost_col and pts_won_col and pts_lost_col:
            rows = []
            for _, row in df_raw.iterrows():
                team = str(row[team_col]).strip()
                if not team or team == 'nan':
                    continue
                try:
                    sets_w = int(float(str(row[sets_won_col]).replace(',', '.')))
                    sets_l = int(float(str(row[sets_lost_col]).replace(',', '.')))
                    pts_w = int(float(str(row[pts_won_col]).replace('.', '').replace(',', '.')))
                    pts_l = int(float(str(row[pts_lost_col]).replace('.', '').replace(',', '.')))
                    rows.append({'Команда': team, 'Сеты': f"{sets_w}:{sets_l}", 'Мячи': f"{pts_w}:{pts_l}"})
                except:
                    continue
            if rows:
                return pd.DataFrame(rows)
        return None
    else:  # text
        return parse_text_to_df(data_source)

def parse_text_to_df(text: str) -> pd.DataFrame:
    lines = text.strip().split('\n')
    data = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ';' in line:
            parts = line.split(';')
            if len(parts) >= 3:
                team = parts[0].strip()
                sets = parts[1].strip()
                points = parts[2].strip()
                if ':' in sets and ':' in points:
                    data.append({'Команда': team, 'Сеты': sets, 'Мячи': points})
            continue
        tokens = re.split(r'\s+', line)
        if len(tokens) < 5:
            continue
        team_parts = []
        numbers = []
        for token in tokens:
            if re.match(r'^[\d\.,]+$', token):
                numbers.append(token)
            else:
                team_parts.append(token)
        if not team_parts or len(numbers) < 4:
            continue
        team = ' '.join(team_parts)
        try:
            sets_w = int(float(numbers[0]))
            sets_l = int(float(numbers[1]))
            pts_w = int(float(numbers[2].replace('.', '').replace(',', '.')))
            pts_l = int(float(numbers[3].replace('.', '').replace(',', '.')))
            data.append({'Команда': team, 'Сеты': f"{sets_w}:{sets_l}", 'Мячи': f"{pts_w}:{pts_l}"})
        except:
            continue
    if data:
        return pd.DataFrame(data)
    return None

# ------------------------------------------------------------
# Функция вероятности выиграть матч (до 3 побед из 5)
# ------------------------------------------------------------
def prob_win_match(p: float) -> float:
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    q = 1 - p
    return 10 * p**3 * q**2 + 5 * p**4 * q + p**5

# ------------------------------------------------------------
# Парсеры для автоматических URL
# ------------------------------------------------------------
def get_parser_by_url(url: str):
    if "volley.ru" in url:
        return RussiaVolleyRuParser()
    elif "dataproject.com" in url:
        return DataProjectParser()
    else:
        return None

def load_teams_from_url(url, combine_phases):
    parser = get_parser_by_url(url)
    if parser is None:
        return None, "URL не поддерживается"
    df, error = parser.fetch_stats(url, combine_phases=combine_phases)
    if df is not None and not df.empty and 'Команда' in df.columns:
        return df, None
    return None, error or "Не удалось загрузить данные"

# ------------------------------------------------------------
# Инициализация Streamlit
# ------------------------------------------------------------
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None
if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}
if 'active_source' not in st.session_state:
    st.session_state.active_source = "auto"
if 'user_tables' not in st.session_state:
    st.session_state.user_tables = {}
if 'selected_user_table' not in st.session_state:
    st.session_state.selected_user_table = None

# ------------------------------------------------------------
# Боковая панель: менеджер пользовательских таблиц
# ------------------------------------------------------------
with st.sidebar:
    st.header("📁 Мои таблицы")
    with st.expander("➕ Новая таблица"):
        table_name = st.text_input("Название таблицы")
        upload_method = st.radio("Способ загрузки", ["Текстовый ввод", "CSV/Excel"])
        if upload_method == "Текстовый ввод":
            text_data = st.text_area("Введите данные", height=250)
            if st.button("Создать таблицу"):
                df_new = parse_text_to_df(text_data)
                if df_new is not None:
                    st.session_state.user_tables[table_name] = df_new
                    st.success(f"Таблица '{table_name}' создана ({len(df_new)} команд)")
                    st.rerun()
                else:
                    st.error("Не удалось распознать данные. Проверьте формат.")
        else:
            uploaded_file = st.file_uploader("CSV или Excel", type=['csv', 'xlsx'])
            if uploaded_file and st.button("Создать таблицу"):
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_new = parse_table_to_df(uploaded_file, 'csv')
                    else:
                        df_new = parse_table_to_df(uploaded_file, 'xlsx')
                    if df_new is not None and not df_new.empty:
                        st.session_state.user_tables[table_name] = df_new
                        st.success(f"Таблица '{table_name}' создана ({len(df_new)} команд)")
                        st.rerun()
                    else:
                        st.error("Не удалось распознать файл. Убедитесь, что он содержит команды, сеты и очки.")
                except Exception as e:
                    st.error(f"Ошибка: {e}")

    if st.session_state.user_tables:
        st.subheader("Доступные таблицы")
        for name, df in st.session_state.user_tables.items():
            col1, col2, col3 = st.columns([3,1,1])
            col1.write(f"**{name}** ({len(df)} команд)")
            if col2.button("Загрузить", key=f"load_{name}"):
                st.session_state.df_teams = df
                st.session_state.active_source = "user_table"
                st.session_state.selected_user_table = name
                st.rerun()
            if col3.button("🗑️", key=f"del_{name}"):
                del st.session_state.user_tables[name]
                if st.session_state.selected_user_table == name:
                    st.session_state.df_teams = None
                    st.session_state.active_source = "auto"
                st.rerun()
        with st.expander("Обновить таблицу"):
            upd_name = st.selectbox("Выберите таблицу", list(st.session_state.user_tables.keys()))
            upd_method = st.radio("Способ", ["Текстовый ввод","CSV/Excel"])
            if upd_method == "Текстовый ввод":
                upd_text = st.text_area("Новые данные", height=150)
                if st.button("Обновить"):
                    df_upd = parse_text_to_df(upd_text)
                    if df_upd is not None:
                        st.session_state.user_tables[upd_name] = df_upd
                        if st.session_state.selected_user_table == upd_name:
                            st.session_state.df_teams = df_upd
                        st.rerun()
                    else:
                        st.error("Не удалось распознать данные")
            else:
                upd_file = st.file_uploader("Файл", type=['csv','xlsx'])
                if upd_file and st.button("Обновить"):
                    try:
                        if upd_file.name.endswith('.csv'):
                            df_upd = parse_table_to_df(upd_file, 'csv')
                        else:
                            df_upd = parse_table_to_df(upd_file, 'xlsx')
                        if df_upd is not None:
                            st.session_state.user_tables[upd_name] = df_upd
                            if st.session_state.selected_user_table == upd_name:
                                st.session_state.df_teams = df_upd
                            st.rerun()
                        else:
                            st.error("Не удалось распознать файл")
                    except Exception as e:
                        st.error(str(e))
    else:
        st.info("Нет сохранённых таблиц. Создайте новую.")

# ------------------------------------------------------------
# Основная область: выбор источника данных
# ------------------------------------------------------------
st.subheader("Источник данных")
src = st.radio(
    "Выберите источник",
    ["Автоматический парсинг (URL)", "Ручной ввод (только одна пара)", "Загруженная таблица"],
    horizontal=True
)
if src == "Автоматический парсинг (URL)":
    st.session_state.active_source = "auto"
elif src == "Ручной ввод (только одна пара)":
    st.session_state.active_source = "manual_pair"
else:
    st.session_state.active_source = "user_table"

# ------------------------------------------------------------
# 1. Автоматический парсинг
# ------------------------------------------------------------
if st.session_state.active_source == "auto":
    with st.form("auto_form"):
        url = st.text_input("URL", placeholder="https://volley.ru/... или dataproject.com...")
        combine = False
        if "dataproject.com" in url:
            combine = st.checkbox("Складывать все этапы")
        if st.form_submit_button("📥 Загрузить данные") and url:
            with st.spinner("Загрузка..."):
                df, err = load_teams_from_url(url, combine)
                if df is not None:
                    st.session_state.df_teams = df
                    st.success(f"Загружено {len(df)} команд")
                else:
                    st.error(err)

# ------------------------------------------------------------
# 2. Ручной ввод одной пары
# ------------------------------------------------------------
elif st.session_state.active_source == "manual_pair":
    st.info("Введите данные для двух команд")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Домашняя**")
        home_name = st.text_input("Название", key="h_name")
        h_sv = st.number_input("Sets V", min_value=0, key="h_sv")
        h_sp = st.number_input("Sets P", min_value=0, key="h_sp")
        h_bv = st.number_input("Balls V", min_value=0, key="h_bv")
        h_bp = st.number_input("Balls P", min_value=0, key="h_bp")
    with col2:
        st.markdown("**Гостевая**")
        away_name = st.text_input("Название", key="a_name")
        a_sv = st.number_input("Sets V", min_value=0, key="a_sv")
        a_sp = st.number_input("Sets P", min_value=0, key="a_sp")
        a_bv = st.number_input("Balls V", min_value=0, key="a_bv")
        a_bp = st.number_input("Balls P", min_value=0, key="a_bp")
    if st.button("Сохранить пару"):
        if home_name and away_name:
            df = pd.DataFrame({
                'Команда': [home_name, away_name],
                'Сеты': [f"{h_sv}:{h_sp}", f"{a_sv}:{a_sp}"],
                'Мячи': [f"{h_bv}:{h_bp}", f"{a_bv}:{a_bp}"]
            })
            st.session_state.df_teams = df
            st.success("Сохранено")

# ------------------------------------------------------------
# 3. Загруженная таблица
# ------------------------------------------------------------
elif st.session_state.active_source == "user_table":
    if st.session_state.user_tables:
        selected = st.selectbox("Выберите таблицу", list(st.session_state.user_tables.keys()))
        if st.button("Активировать"):
            st.session_state.df_teams = st.session_state.user_tables[selected]
            st.session_state.selected_user_table = selected
            st.success(f"Активирована '{selected}'")
    else:
        st.warning("Нет таблиц. Создайте в боковой панели.")

# ------------------------------------------------------------
# Прогноз
# ------------------------------------------------------------
if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
    if 'Команда' not in st.session_state.df_teams.columns:
        st.error("Некорректный формат: отсутствует колонка 'Команда'")
    else:
        teams = st.session_state.df_teams['Команда'].tolist()
        st.subheader("📊 Прогноз на матч")
        col1, col2 = st.columns(2)
        with col1:
            home = st.selectbox("Домашняя", teams, key="home_sel")
            home_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
            h_sv, h_sp = map(int, home_row['Сеты'].split(':'))
            h_bv, h_bp = map(int, home_row['Мячи'].split(':'))
            p_home_set = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
            st.caption(f"Сеты: {h_sv}:{h_sp} | Мячи: {h_bv}:{h_bp} | % сетов: {p_home_set:.1%}")
        with col2:
            away = st.selectbox("Гостевая", teams, key="away_sel")
            away_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
            a_sv, a_sp = map(int, away_row['Сеты'].split(':'))
            a_bv, a_bp = map(int, away_row['Мячи'].split(':'))
            p_away_set = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
            st.caption(f"Сеты: {a_sv}:{a_sp} | Мячи: {a_bv}:{a_bp} | % сетов: {p_away_set:.1%}")

        if st.button("Рассчитать котировки", key="calc"):
            if home == away:
                st.error("Выберите разные команды")
            else:
                # Прогноз по сетам
                p_home = h_sv / (h_sv + h_sp) if (h_sv + h_sp) > 0 else 0.5
                p_away = a_sv / (a_sv + a_sp) if (a_sv + a_sp) > 0 else 0.5
                prob_home_match = prob_win_match(p_home)
                prob_away_match = prob_win_match(p_away)
                total = prob_home_match + prob_away_match
                prob_home_norm = prob_home_match / total
                prob_away_norm = prob_away_match / total
                if prob_home_norm > prob_away_norm:
                    favorite = home
                    fav_prob = prob_home_norm
                else:
                    favorite = away
                    fav_prob = prob_away_norm
                margin = 0.05
                odds = (1 - margin) / fav_prob
                st.subheader("📈 Прогноз по сетам")
                st.write(f"**Победа {favorite} – коэффициент {odds:.2f}**")
                st.caption("Вероятность победы в матче рассчитана через биномиальное распределение (best of 5) и нормализована.")

                # Прогноз по очкам (фора)
                total_matches_h = (h_sv + h_sp) // 3 if (h_sv + h_sp) > 0 else 30
                total_matches_a = (a_sv + a_sp) // 3 if (a_sv + a_sp) > 0 else 30
                total_matches = max(total_matches_h, total_matches_a, 1)
                home_avg_pts = (h_bv - h_bp) / total_matches
                away_avg_pts = (a_bv - a_bp) / total_matches
                handicap = round(home_avg_pts - away_avg_pts, 1)
                st.subheader("⚖️ Прогноз по очкам (фора)")
                if handicap > 0:
                    st.success(f"Фора на матч: {handicap} (в пользу хозяев)")
                elif handicap < 0:
                    st.success(f"Фора на матч: {handicap} (в пользу гостей)")
                else:
                    st.info("Фора близка к нулю")
                st.caption("Средняя разница очков за матч (оценка).")

                # Личные встречи (ручной ввод) – без изменений
                st.divider()
                st.subheader("📋 Личные встречи (ручной ввод)")
                all_teams = teams if len(teams) > 1 else [home, away]
                with st.expander("➕ Добавить личную встречу"):
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        hh = st.selectbox("Хозяева", all_teams, key="h2h_h")
                    with col_b:
                        ha = st.selectbox("Гости", all_teams, key="h2h_a")
                    with col_c:
                        sets_h2h = st.text_input("Счёт по сетам", placeholder="3:1")
                    pts_h2h = st.number_input("Фора по очкам (+, если хозяева выиграли)", step=0.5)
                    date_h2h = st.text_input("Дата", placeholder="01.01.2026")
                    if st.button("Добавить", key="add_h2h"):
                        key = (hh, ha)
                        st.session_state.h2h_manual.setdefault(key, []).append({
                            'Дата': date_h2h or "(нет даты)",
                            'Хозяева': hh,
                            'Гости': ha,
                            'Счёт по сетам': sets_h2h,
                            'Фора по очкам': pts_h2h
                        })
                        st.rerun()

                key_pair = (home, away)
                rev = (away, home)
                h2h_list = []
                for m in st.session_state.h2h_manual.get(key_pair, []):
                    h2h_list.append(m)
                for m in st.session_state.h2h_manual.get(rev, []):
                    new_m = m.copy()
                    new_m['Хозяева'] = home
                    new_m['Гости'] = away
                    new_m['Фора по очкам'] = -m['Фора по очкам']
                    h2h_list.append(new_m)

                if h2h_list:
                    df_h2h = pd.DataFrame(h2h_list)
                    st.subheader(f"История встреч: {home} – {away}")
                    st.dataframe(df_h2h[['Дата','Хозяева','Гости','Счёт по сетам','Фора по очкам']])
                    if st.button("Очистить историю этой пары"):
                        st.session_state.h2h_manual.pop(key_pair, None)
                        st.session_state.h2h_manual.pop(rev, None)
                        st.rerun()
                else:
                    st.info("Нет данных о личных встречах. Добавьте вручную.")
else:
    if st.session_state.df_teams is not None and st.session_state.df_teams.empty:
        st.warning("Активная таблица пуста")
    else:
        st.info("Выберите источник данных и загрузите команды.")
