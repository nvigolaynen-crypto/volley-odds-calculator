import streamlit as st
import pandas as pd
import io
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser

# ------------------------------------------------------------
# Функции парсинга
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
        return None, "URL не поддерживается. Используйте volley.ru или dataproject.com"
    df, error = parser.fetch_stats(url, combine_phases=combine_phases)
    if df is not None and not df.empty and 'Команда' in df.columns:
        return df, None
    else:
        return None, error or "Не удалось загрузить данные"

# ------------------------------------------------------------
# Функция для парсинга текста (ручной ввод таблицы)
# ------------------------------------------------------------
def parse_text_to_df(text: str) -> pd.DataFrame:
    """Преобразует текст вида 'Команда;Сеты;Мячи' в DataFrame"""
    data = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split(';')
        if len(parts) >= 3:
            team = parts[0].strip()
            sets = parts[1].strip()
            points = parts[2].strip()
            if ':' in sets and ':' in points:
                data.append({'Команда': team, 'Сеты': sets, 'Мячи': points})
    if data:
        return pd.DataFrame(data)
    return None

# ------------------------------------------------------------
# Настройка страницы
# ------------------------------------------------------------
st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

# Инициализация состояния
if 'df_teams' not in st.session_state:
    st.session_state.df_teams = None            # текущая активная таблица (DataFrame)
if 'h2h_manual' not in st.session_state:
    st.session_state.h2h_manual = {}
if 'active_source' not in st.session_state:
    st.session_state.active_source = "auto"     # "auto", "manual", "user_table"
if 'user_tables' not in st.session_state:
    st.session_state.user_tables = {}           # {имя_таблицы: DataFrame}
if 'selected_user_table' not in st.session_state:
    st.session_state.selected_user_table = None
if 'manual_mode_for_pair' not in st.session_state:
    # для ручного ввода только одной пары (без таблицы)
    st.session_state.manual_pair_data = {
        'home': {'name': '', 'sets_v': 0, 'sets_p': 0, 'balls_v': 0, 'balls_p': 0},
        'away': {'name': '', 'sets_v': 0, 'sets_p': 0, 'balls_v': 0, 'balls_p': 0}
    }

# ------------------------------------------------------------
# Боковая панель: менеджер пользовательских таблиц
# ------------------------------------------------------------
with st.sidebar:
    st.header("📁 Мои таблицы")
    
    # Форма создания новой таблицы
    with st.expander("➕ Новая таблица"):
        table_name = st.text_input("Название таблицы", key="new_table_name")
        upload_method = st.radio("Способ загрузки", ["Текстовый ввод", "CSV/Excel"], key="upload_method")
        df_new = None
        if upload_method == "Текстовый ввод":
            text_data = st.text_area("Введите данные (Команда;Сеты;Мячи, каждая с новой строки)", height=200,
                                     help="Пример:\nЗенит-Казань;87:24;2655:2259\nДинамо-Москва;76:30;2450:2200")
            if st.button("Создать таблицу", key="create_txt"):
                df_new = parse_text_to_df(text_data)
                if df_new is not None and not df_new.empty:
                    st.session_state.user_tables[table_name] = df_new
                    st.success(f"Таблица '{table_name}' создана ({len(df_new)} команд)")
                    st.rerun()
                else:
                    st.error("Не удалось распознать данные. Проверьте формат.")
        else:  # CSV/Excel
            uploaded_file = st.file_uploader("Загрузите файл", type=['csv', 'xlsx'], key="table_file")
            if uploaded_file and st.button("Создать таблицу", key="create_file"):
                try:
                    if uploaded_file.name.endswith('.csv'):
                        df_new = pd.read_csv(uploaded_file, sep=None, engine='python')
                    else:
                        df_new = pd.read_excel(uploaded_file)
                    # Проверяем наличие колонок
                    required = ['Команда', 'Сеты', 'Мячи']
                    if all(col in df_new.columns for col in required):
                        st.session_state.user_tables[table_name] = df_new[required]
                        st.success(f"Таблица '{table_name}' создана ({len(df_new)} команд)")
                        st.rerun()
                    else:
                        st.error(f"Файл должен содержать колонки: {', '.join(required)}")
                except Exception as e:
                    st.error(f"Ошибка чтения файла: {e}")
    
    # Отображение списка таблиц с возможностью загрузки, удаления, обновления
    if st.session_state.user_tables:
        st.subheader("Доступные таблицы")
        for name, df in st.session_state.user_tables.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"**{name}** ({len(df)} команд)")
            if col2.button("Загрузить", key=f"load_{name}"):
                st.session_state.df_teams = df
                st.session_state.active_source = "user_table"
                st.session_state.selected_user_table = name
                st.success(f"Таблица '{name}' активирована")
                st.rerun()
            if col3.button("🗑️", key=f"del_{name}"):
                del st.session_state.user_tables[name]
                if st.session_state.selected_user_table == name:
                    st.session_state.df_teams = None
                    st.session_state.active_source = "auto"
                st.rerun()
        
        # Обновление выбранной таблицы (перезагрузка)
        st.subheader("Обновить таблицу")
        update_name = st.selectbox("Выберите таблицу для обновления", list(st.session_state.user_tables.keys()), key="update_select")
        update_method = st.radio("Способ обновления", ["Текстовый ввод", "CSV/Excel"], key="update_method")
        if update_method == "Текстовый ввод":
            new_text = st.text_area("Новые данные", height=150, key="update_text")
            if st.button("Обновить", key="update_txt"):
                df_new = parse_text_to_df(new_text)
                if df_new is not None:
                    st.session_state.user_tables[update_name] = df_new
                    if st.session_state.selected_user_table == update_name:
                        st.session_state.df_teams = df_new
                    st.success("Таблица обновлена")
                    st.rerun()
        else:
            new_file = st.file_uploader("Загрузите новый файл", type=['csv', 'xlsx'], key="update_file")
            if new_file and st.button("Обновить", key="update_file_btn"):
                try:
                    if new_file.name.endswith('.csv'):
                        df_new = pd.read_csv(new_file, sep=None, engine='python')
                    else:
                        df_new = pd.read_excel(new_file)
                    if all(col in df_new.columns for col in ['Команда', 'Сеты', 'Мячи']):
                        st.session_state.user_tables[update_name] = df_new[['Команда', 'Сеты', 'Мячи']]
                        if st.session_state.selected_user_table == update_name:
                            st.session_state.df_teams = df_new
                        st.success("Таблица обновлена")
                        st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")
    else:
        st.info("Нет сохранённых таблиц. Создайте новую выше.")

# ------------------------------------------------------------
# Основная область: выбор источника данных
# ------------------------------------------------------------
st.subheader("Источник данных для прогноза")

src = st.radio(
    "Выберите источник команд",
    ["Автоматический парсинг (URL)", "Ручной ввод (только одна пара)", "Загруженная таблица"],
    horizontal=True,
    key="src_radio"
)

# Обработка смены источника
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
        url = st.text_input("URL турнирной таблицы", placeholder="https://volley.ru/... или https://...dataproject.com...")
        combine_phases = False
        if "dataproject.com" in url:
            combine_phases = st.checkbox("Складывать все этапы (только Data Project)")
        load_btn = st.form_submit_button("📥 Загрузить данные")
        if load_btn and url:
            with st.spinner("Загрузка..."):
                df, err = load_teams_from_url(url, combine_phases)
                if df is not None:
                    st.session_state.df_teams = df
                    st.success(f"Загружено {len(df)} команд")
                else:
                    st.error(err)

# ------------------------------------------------------------
# 2. Ручной ввод только одной пары (без таблицы)
# ------------------------------------------------------------
elif st.session_state.active_source == "manual_pair":
    st.info("Введите данные для двух команд (домашней и гостевой).")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Домашняя команда**")
        home_name = st.text_input("Название", key="pair_home_name")
        home_sets_v = st.number_input("Sets V", min_value=0, step=1, key="pair_home_sets_v")
        home_sets_p = st.number_input("Sets P", min_value=0, step=1, key="pair_home_sets_p")
        home_balls_v = st.number_input("Balls V", min_value=0, step=1, key="pair_home_balls_v")
        home_balls_p = st.number_input("Balls P", min_value=0, step=1, key="pair_home_balls_p")
    with col2:
        st.markdown("**Гостевая команда**")
        away_name = st.text_input("Название", key="pair_away_name")
        away_sets_v = st.number_input("Sets V", min_value=0, step=1, key="pair_away_sets_v")
        away_sets_p = st.number_input("Sets P", min_value=0, step=1, key="pair_away_sets_p")
        away_balls_v = st.number_input("Balls V", min_value=0, step=1, key="pair_away_balls_v")
        away_balls_p = st.number_input("Balls P", min_value=0, step=1, key="pair_away_balls_p")
    
    if st.button("Сохранить пару для прогноза"):
        if home_name and away_name:
            # Создаём временный DataFrame из двух строк
            data = {
                'Команда': [home_name, away_name],
                'Сеты': [f"{home_sets_v}:{home_sets_p}", f"{away_sets_v}:{away_sets_p}"],
                'Мячи': [f"{home_balls_v}:{home_balls_p}", f"{away_balls_v}:{away_balls_p}"]
            }
            st.session_state.df_teams = pd.DataFrame(data)
            st.success("Данные сохранены")
        else:
            st.error("Введите названия обеих команд")

# ------------------------------------------------------------
# 3. Загруженная таблица (из менеджера)
# ------------------------------------------------------------
elif st.session_state.active_source == "user_table":
    if st.session_state.user_tables:
        selected = st.selectbox("Выберите таблицу", list(st.session_state.user_tables.keys()), key="active_table_select")
        if st.button("Активировать"):
            st.session_state.df_teams = st.session_state.user_tables[selected]
            st.session_state.selected_user_table = selected
            st.success(f"Активирована таблица '{selected}'")
    else:
        st.warning("Нет доступных таблиц. Создайте таблицу в боковой панели.")
        st.session_state.df_teams = None

# ------------------------------------------------------------
# Прогноз (есть активная таблица)
# ------------------------------------------------------------
if st.session_state.df_teams is not None and not st.session_state.df_teams.empty:
    if 'Команда' not in st.session_state.df_teams.columns:
        st.error("Некорректный формат таблицы: отсутствует колонка 'Команда'")
    else:
        teams = st.session_state.df_teams['Команда'].tolist()
        st.subheader("📊 Прогноз на матч")
        col1, col2 = st.columns(2)
        with col1:
            home = st.selectbox("Домашняя команда", teams, key="home_select")
            home_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == home].iloc[0]
            h_sets_v, h_sets_p = map(int, home_row['Сеты'].split(':'))
            h_balls_v, h_balls_p = map(int, home_row['Мячи'].split(':'))
            st.caption(f"Сеты: {h_sets_v}:{h_sets_p} | Мячи: {h_balls_v}:{h_balls_p}")
        with col2:
            away = st.selectbox("Гостевая команда", teams, key="away_select")
            away_row = st.session_state.df_teams[st.session_state.df_teams['Команда'] == away].iloc[0]
            a_sets_v, a_sets_p = map(int, away_row['Сеты'].split(':'))
            a_balls_v, a_balls_p = map(int, away_row['Мячи'].split(':'))
            st.caption(f"Сеты: {a_sets_v}:{a_sets_p} | Мячи: {a_balls_v}:{a_balls_p}")

        if st.button("Рассчитать котировки", key="calc_btn"):
            if home == away:
                st.error("Выберите разные команды.")
            else:
                # Прогноз по сетам: фаворит
                home_wr = h_sets_v / (h_sets_v + h_sets_p) if (h_sets_v + h_sets_p) > 0 else 0.5
                away_wr = a_sets_v / (a_sets_v + a_sets_p) if (a_sets_v + a_sets_p) > 0 else 0.5
                if home_wr > away_wr:
                    favorite = home
                    fav_winrate = home_wr
                else:
                    favorite = away
                    fav_winrate = away_wr
                odds_fav = (1 - 0.05) / fav_winrate if fav_winrate > 0 else 0
                st.subheader("📈 Прогноз по сетам")
                st.write(f"**Победа {favorite} – коэффициент {odds_fav:.2f}**")
                
                # Прогноз по очкам: фора на хозяев
                total_matches = (h_sets_v + h_sets_p) // 3 if (h_sets_v + h_sets_p) > 0 else 30
                home_avg = (h_balls_v - h_balls_p) / total_matches
                away_avg = (a_balls_v - a_balls_p) / total_matches
                handicap = round(home_avg - away_avg, 1)
                st.subheader("⚖️ Прогноз по очкам (фора)")
                if handicap > 0:
                    st.success(f"Фора на матч: {handicap} (в пользу хозяев)")
                elif handicap < 0:
                    st.success(f"Фора на матч: {handicap} (в пользу гостей)")
                else:
                    st.info("Фора близка к нулю")
                st.caption("Средняя разница очков за матч (хозяева − гости)")
                
                # Личные встречи (ручной ввод)
                st.divider()
                st.subheader("📋 Личные встречи (ручной ввод)")
                # ... (здесь можно вставить предыдущий блок с личными встречами, но для краткости опустим, он такой же)
                # В реальном проекте скопируйте сюда блок из предыдущей версии
else:
    if st.session_state.df_teams is not None and st.session_state.df_teams.empty:
        st.warning("Активная таблица пуста. Загрузите данные.")
    else:
        st.info("Выберите источник данных и загрузите команды.")
