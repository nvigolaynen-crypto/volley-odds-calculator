import re
import requests
from bs4 import BeautifulSoup
from .base_parser import BaseParser

class ItalyParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
        }
        session = requests.Session()
        session.headers.update(headers)

        # Предварительный запрос главной страницы для получения cookies
        try:
            session.get('https://www.legavolley.it/', timeout=10)
        except:
            pass

        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки страницы: {e}"

        soup = BeautifulSoup(response.text, 'html.parser')

        # === Отладка: сохраняем HTML для анализа ===
        with open('debug_italy.html', 'w', encoding='utf-8') as f:
            f.write(response.text)

        # Поиск таблицы разными способами
        table = soup.find('table', id='GareGiornata')
        if not table:
            table = soup.find('table', attrs={'id': re.compile(r'GareGiornata|Classifica', re.I)})
        if not table:
            table = soup.find('table', class_=re.compile(r'classifica', re.I))
        if not table:
            # Ищем div с классом, содержащим "classifica", потом внутри таблицу
            div_class = soup.find('div', class_=re.compile(r'classifica', re.I))
            if div_class:
                table = div_class.find('table')
        if not table:
            return None, "Таблица не найдена. Проверьте debug_italy.html на сервере."

        # Строки с данными
        rows = table.find_all('tr', id='EvenRow')
        if not rows:
            rows = [tr for tr in table.find_all('tr') if tr.find('span', class_='pos')]

        teams = []
        sets_list = []
        points_list = []

        for row in rows:
            # Название команды (ячейка с colspan=2)
            name_cell = row.find('td', colspan='2')
            if not name_cell:
                continue
            pos_span = name_cell.find('span', class_='pos')
            if pos_span:
                raw = name_cell.get_text(strip=True)
                name = re.sub(r'^\d+\s*', '', raw).strip()
            else:
                name = name_cell.get_text(strip=True)
            if not name:
                continue
            teams.append(name)

            # Ячейки с числами
            tds = row.find_all('td', align='center')
            if len(tds) >= 13:
                set_w = tds[4].get_text(strip=True)      # выигранные сеты
                set_l = tds[5].get_text(strip=True)      # проигранные сеты
                pts_f = tds[11].get_text(strip=True).replace('.', '')  # очки забитые
                pts_a = tds[12].get_text(strip=True).replace('.', '')  # очки пропущенные
            else:
                # Альтернативный парсинг – ищем подряд два числа (сеты) и два числа с точкой (очки)
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
                    continue

            sets_list.append(f"{set_w}:{set_l}")
            points_list.append(f"{pts_f}:{pts_a}")

        if not teams:
            return None, "Не удалось извлечь команды из таблицы."

        import pandas as pd
        df = pd.DataFrame({
            'Команда': teams,
            'Сеты': sets_list,
            'Мячи': points_list
        })
        return df, None

    def fetch_head_to_head(self, team1: str, team2: str):
        """Для legavolley.it история встреч не парсится автоматически."""
        return None
