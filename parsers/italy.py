"""
Парсер для итальянской лиги legavolley.it
"""
import re
import requests
from bs4 import BeautifulSoup
from .base_parser import BaseParser

class ItalyParser(BaseParser):
    """Парсер турнирной таблицы с legavolley.it"""

    def fetch_stats(self, url: str, combine_phases: bool = False):
        """
        Загружает таблицу с legavolley.it и возвращает DataFrame с колонками:
        Команда, Сеты, Мячи
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
            'Referer': 'https://www.legavolley.it/',
        }
        session = requests.Session()
        session.headers.update(headers)

        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки страницы: {e}"

        soup = BeautifulSoup(response.text, 'html.parser')

        # Поиск таблицы с результатами (обычно id="GareGiornata")
        table = soup.find('table', id='GareGiornata')
        if not table:
            table = soup.find('table', attrs={'id': re.compile(r'GareGiornata|Classifica', re.I)})
        if not table:
            # Резерв: любая таблица с классом, содержащим "classifica"
            table = soup.find('table', class_=re.compile(r'classifica', re.I))
        if not table:
            return None, "Таблица не найдена. Убедитесь, что передан правильный URL."

        # Строки с данными команд: у них обычно есть атрибут id="EvenRow"
        rows = table.find_all('tr', id='EvenRow')
        if not rows:
            # Ищем строки, в которых есть span с классом "pos"
            rows = [tr for tr in table.find_all('tr') if tr.find('span', class_='pos')]

        teams = []
        sets_list = []
        points_list = []

        for row in rows:
            # Ячейка с названием команды (colspan=2)
            name_cell = row.find('td', colspan='2')
            if not name_cell:
                continue

            # Извлекаем название, убирая номер позиции
            pos_span = name_cell.find('span', class_='pos')
            if pos_span:
                raw = name_cell.get_text(strip=True)
                name = re.sub(r'^\d+\s*', '', raw).strip()
            else:
                name = name_cell.get_text(strip=True)

            if not name:
                continue
            teams.append(name)

            # Сбор ячеек с цифрами (выравнивание по центру)
            tds = row.find_all('td', align='center')
            if len(tds) >= 13:
                # Стандартное расположение: сеты выигр/проигр в ячейках 4 и 5, очки забитые/пропущенные в 11 и 12
                set_w = tds[4].get_text(strip=True)
                set_l = tds[5].get_text(strip=True)
                pts_f = tds[11].get_text(strip=True).replace('.', '')   # убираем разделитель тысяч
                pts_a = tds[12].get_text(strip=True).replace('.', '')
            else:
                # Альтернативный поиск: находим два числа подряд (сеты) и два числа с точкой (очки)
                numbers = []
                for td in tds:
                    text = td.get_text(strip=True)
                    if text.isdigit():
                        numbers.append(text)
                    elif '.' in text and text.replace('.', '').isdigit():
                        numbers.append(text.replace('.', ''))
                if len(numbers) >= 4:
                    set_w, set_l, pts_f, pts_a = numbers[:4]
                else:
                    # Недостаточно данных – пропускаем команду
                    continue

            sets_list.append(f"{set_w}:{set_l}")
            points_list.append(f"{pts_f}:{pts_a}")

        if not teams:
            return None, "Не удалось извлечь данные команд. Возможно, изменилась структура страницы."

        # Формируем DataFrame
        import pandas as pd
        df = pd.DataFrame({
            'Команда': teams,
            'Сеты': sets_list,
            'Мячи': points_list
        })
        return df, None
