import re
import requests
from bs4 import BeautifulSoup
from .base_parser import BaseParser

class ItalyParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
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
            return None, f"Ошибка загрузки: {e}"

        soup = BeautifulSoup(response.text, 'html.parser')

        # Сохраняем HTML для отладки (полезно на Render)
        with open('debug_italy.html', 'w', encoding='utf-8') as f:
            f.write(response.text)

        # Ищем таблицу
        table = soup.find('table', id='GareGiornata')
        if not table:
            # Дополнительные варианты
            table = soup.find('table', attrs={'id': re.compile(r'GareGiornata|Classifica', re.I)})
        if not table:
            table = soup.find('table', class_=re.compile(r'classifica', re.I))
        if not table:
            # Попробуем найти любой div с классом, содержащим "classifica", а внутри таблицу
            div_class = soup.find('div', class_=re.compile(r'classifica', re.I))
            if div_class:
                table = div_class.find('table')
        if not table:
            return None, "Таблица не найдена. Проверьте debug_italy.html"

        rows = table.find_all('tr', id='EvenRow')
        if not rows:
            rows = [tr for tr in table.find_all('tr') if tr.find('span', class_='pos')]

        teams = []
        sets_list = []
        points_list = []

        for row in rows:
            name_cell = row.find('td', colspan='2')
            if not name_cell:
                continue
            pos_span = name_cell.find('span', class_='pos')
            if pos_span:
                name = re.sub(r'^\d+\s*', '', name_cell.get_text(strip=True)).strip()
            else:
                name = name_cell.get_text(strip=True)
            if not name:
                continue
            teams.append(name)

            tds = row.find_all('td', align='center')
            if len(tds) >= 13:
                set_w = tds[4].get_text(strip=True)
                set_l = tds[5].get_text(strip=True)
                pts_f = tds[11].get_text(strip=True).replace('.', '')
                pts_a = tds[12].get_text(strip=True).replace('.', '')
            else:
                # Альтернативный сбор
                nums = []
                for td in tds:
                    txt = td.get_text(strip=True)
                    if txt.isdigit():
                        nums.append(txt)
                    elif '.' in txt and txt.replace('.', '').isdigit():
                        nums.append(txt.replace('.', ''))
                if len(nums) >= 4:
                    set_w, set_l, pts_f, pts_a = nums[:4]
                else:
                    continue
            sets_list.append(f"{set_w}:{set_l}")
            points_list.append(f"{pts_f}:{pts_a}")

        if not teams:
            return None, "Не удалось извлечь команды"

        import pandas as pd
        df = pd.DataFrame({'Команда': teams, 'Сеты': sets_list, 'Мячи': points_list})
        return df, None

    def fetch_head_to_head(self, team1: str, team2: str):
        # Если не нужна история встреч – возвращаем None
        return None
