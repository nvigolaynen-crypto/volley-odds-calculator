import streamlit as st
from parsers.russia_volleyru import RussiaVolleyRuParser
from parsers.dataproject import DataProjectParser
from parsers.poland import PolandParser
from parsers.italy import ItalyParser
from parsers.turkey import TurkeyParser

PARSERS = {
    "Россия (volley.ru)": RussiaVolleyRuParser(),
    "Data Project (Универсальный)": DataProjectParser(),
    "Польша": PolandParser(),
    "Италия": ItalyParser(),
    "Турция": TurkeyParser(),
}

st.set_page_config(page_title="Волейбольная статистика", layout="wide")
st.title("🏐 Волейбольная статистика")

country = st.selectbox("Выберите страну / источник", list(PARSERS.keys()))
parser = PARSERS[country]

if country == "Россия (volley.ru)":
    url = st.text_input(
        "Введите URL страницы этапа (например, предварительный этап)",
        "https://volley.ru/calendar/01JYGFSGNBJZ0G0CNQFRFJ0ADA/predvaritelnyy"
    )
    if st.button("Парсить") and url:
        with st.spinner("Парсинг..."):
            try:
                df_sets, _ = parser.fetch_stats(url)
                st.subheader("Результаты (сеты и мячи)")
                st.dataframe(df_sets)
            except Exception as e:
                st.error(f"Ошибка: {e}")

elif country == "Data Project (Универсальный)":
    st.info("Укажите аббревиатуру федерации и ID соревнования (или ID матча).")
    fed = st.text_input("Аббревиатура федерации (fed)", "cbv")
    comp_id = st.text_input("ID соревнования (comp)", "")
    match_id = st.text_input("ID матча (match)", "")

    if st.button("Парсить"):
        if not comp_id and not match_id:
            st.error("Укажите хотя бы comp_id или match_id")
        else:
            with st.spinner("Парсинг..."):
                try:
                    df, _ = parser.fetch_stats(fed, comp_id, match_id)
                    st.subheader("Результаты парсинга")
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Ошибка: {e}")

else:
    url = st.text_input("Введите URL страницы с результатами")
    if st.button("Парсить") and url:
        with st.spinner("Парсинг..."):
            df_sets, _ = parser.fetch_stats(url)
            if not df_sets.empty:
                st.dataframe(df_sets)
            else:
                st.warning("Парсер для этой страны пока не реализован")