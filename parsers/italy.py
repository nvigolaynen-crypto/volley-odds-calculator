import re
from curl_cffi import requests
from bs4 import BeautifulSoup
from .base_parser import BaseParser

class ItalyParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        """
        Парсит турнирную таблицу legavolley.it с обходом Cloudflare через curl_cffi.
        """
        # Заголовки как в реальном браузере Chrome
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Referer': 'https://www.legavolley.it/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            # Создаём сессию с имитацией Chrome 120 (TLS-отпечаток)
            # Параметр impersonate="chrome120" – ключевой для обхода блокировок
            with requests.Session(impersonate="chrome120") as session:
                # Предварительный запрос главной страницы (необязательно, но помогает)
                session.get('https://www.legavolley.it/', headers=headers, timeout=15)
                # Основной запрос к таблице
                response = session.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                html = response.text
        except Exception as e:
            return None, f"Ошибка загрузки страницы с curl_cffi: {e}"

        soup = BeautifulSoup(html, 'html.parser')

        # Поиск таблицы (как и раньше)
        table = soup.find('table', id='GareGiornata')
        if not table:
            table = soup.find('table', attrs={'id': re.compile(r'GareGiornata|Classifica', re.I)})
        if not table:
            table = soup.find('table', class_=re.compile(r'classifica', re.I))
        if not table:
            # Ищем в div с классом classifica
            div_class = soup.find('div', class_=re.compile(r'classifica', re.I))
            if div_class:
                table = div_class.find('table')
        if not table:
            return None, "Таблица не найдена. Возможно, структура страницы изменилась."

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
        """История встреч не парсится автоматически."""
        return None
