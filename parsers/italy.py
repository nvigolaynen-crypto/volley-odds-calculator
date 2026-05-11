import re
import cloudscraper
from bs4 import BeautifulSoup
from .base_parser import BaseParser

class ItalyParser(BaseParser):
    def fetch_stats(self, url: str, combine_phases: bool = False):
        # Создаём scraper, который автоматически обходит Cloudflare и другие защиты
        scraper = cloudscraper.create_scraper()

        # Дополнительные заголовки для маскировки под реальный браузер
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
            'Referer': 'https://www.legavolley.it/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }

        try:
            # Предварительный запрос главной страницы для получения cookies (опционально, но полезно)
            scraper.get('https://www.legavolley.it/', timeout=10, headers=headers)
            # Основной запрос к таблице
            response = scraper.get(url, timeout=15, headers=headers)
            response.raise_for_status()
        except Exception as e:
            return None, f"Ошибка загрузки страницы: {e}"

        soup = BeautifulSoup(response.text, 'html.parser')

        # === Отладка: сохраняем HTML (можно удалить или закомментировать) ===
        # with open('debug_italy.html', 'w', encoding='utf-8') as f:
        #     f.write(response.text)

        # Поиск таблицы
        table = soup.find('table', id='GareGiornata')
        if not table:
            table = soup.find('table', attrs={'id': re.compile(r'GareGiornata|Classifica', re.I)})
        if not table:
            table = soup.find('table', class_=re.compile(r'classifica', re.I))
        if not table:
            div_class = soup.find('div', class_=re.compile(r'classifica', re.I))
            if div_class:
                table = div_class.find('table')
        if not table:
            return None, "Таблица не найдена. Возможно, изменилась структура страницы."

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
        """Для legavolley.it автоматическая история встреч не реализована."""
        return None
