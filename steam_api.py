import requests
import time
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

class SteamMarketAPI:
    BASE_URL = "https://steamcommunity.com/market/priceoverview/"
    HISTORY_URL = "https://steamcommunity.com/market/pricehistory/"
    SEARCH_URL = "https://steamcommunity.com/market/search/render/"

    def __init__(self):
        self.session = requests.Session()
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour cache

    def _parse_price(self, price_str: str) -> float:
        """Парсинг цены из строки"""
        try:
            # Удаляем все нечисловые символы, кроме точки и запятой
            price_str = ''.join(c for c in price_str if c.isdigit() or c in '.,')
            # Заменяем запятую на точку и конвертируем в float
            return float(price_str.replace(',', '.'))
        except (ValueError, AttributeError):
            return 0.0

    def get_item_price(self, item_name: str) -> Optional[Dict]:
        """Получение текущей цены предмета"""
        try:
            params = {
                'appid': '730',  # CS:GO
                'currency': '5',  # RUB
                'market_hash_name': item_name
            }

            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return None

    def search_items(self, query: str, start: int = 0, count: int = 100) -> List[Dict]:
        """Поиск предметов по названию с пагинацией"""
        try:
            params = {
                'appid': '730',
                'query': query,
                'start': start,
                'count': count,
                'sort_column': 'price',  # Сортировка по цене
                'sort_dir': 'asc',       # По возрастанию
                'norender': 1            # Только JSON ответ
            }

            response = self.session.get(self.SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('results', [])
        except requests.RequestException:
            return []

    def find_profitable_items(self, min_profit_percent: float = 5.0, max_items: int = 500) -> List[Dict]:
        """Поиск выгодных предметов для перепродажи"""
        profitable_items = []
        processed_items = 0
        start = 0
        batch_size = 100

        while processed_items < max_items:
            items = self.search_items("", start, batch_size)
            if not items:
                break

            for item in items:
                try:
                    name = item['name']

                    # Парсим текущую цену
                    current_price = self._parse_price(item.get('sell_price_text', item.get('price', '0')))
                    if current_price <= 0:
                        continue

                    # Получаем историю цен
                    history_data = self.get_item_price(name)
                    if not history_data:
                        continue

                    # Парсим цены из истории
                    lowest_price = self._parse_price(history_data.get('lowest_price', '0'))
                    median_price = self._parse_price(history_data.get('median_price', '0'))
                    volume = int(history_data.get('volume', '0'))

                    if lowest_price <= 0 or median_price <= 0:
                        continue

                    # Рассчитываем потенциальную прибыль
                    potential_profit = median_price - current_price
                    potential_profit_percent = (potential_profit / current_price) * 100
                    price_volatility = ((median_price - lowest_price) / lowest_price) * 100

                    # Проверяем критерии выгодности
                    if (potential_profit_percent >= min_profit_percent and 
                        price_volatility >= 5 and 
                        volume > 10):  # Минимальный объем продаж

                        profitable_items.append({
                            'name': name,
                            'current_price': current_price,
                            'median_price': median_price,
                            'lowest_price': lowest_price,
                            'profit_percent': potential_profit_percent,
                            'volatility': price_volatility,
                            'volume': volume
                        })

                except Exception as e:
                    continue

                processed_items += 1
                if processed_items >= max_items:
                    break

            start += batch_size
            time.sleep(0.5)  # Небольшая задержка между запросами

        # Сортируем по потенциальной прибыли и объему продаж
        profitable_items.sort(key=lambda x: (x['profit_percent'] * x['volume'], x['volatility']), reverse=True)
        return profitable_items