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
                'appid': '730',  # CS:GO
                'query': query,
                'start': start,
                'count': count,
                'search_descriptions': 0,  # Не ищем в описаниях
                'sort_column': 'popular',  # Сортировка по популярности
                'sort_dir': 'desc',        # По убыванию
                'norender': 1              # Только JSON ответ
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

        # Получаем предметы порциями
        while processed_items < max_items:
            # Ищем популярные предметы
            items = self.search_items("", start, batch_size)
            if not items:
                break

            for item in items:
                try:
                    name = item['name']
                    sell_listings = int(item.get('sell_listings', 0))  # Количество активных продаж

                    # Пропускаем предметы с малым количеством продаж
                    if sell_listings < 10:
                        continue

                    # Парсим текущую цену
                    current_price = self._parse_price(item.get('sell_price_text', item.get('price', '0')))
                    if current_price <= 0:
                        continue

                    # Получаем текущие рыночные данные
                    market_data = self.get_item_price(name)
                    if not market_data:
                        continue

                    # Парсим цены
                    lowest_price = self._parse_price(market_data.get('lowest_price', '0'))
                    median_price = self._parse_price(market_data.get('median_price', '0'))
                    volume = int(market_data.get('volume', '0'))

                    if lowest_price <= 0 or median_price <= 0 or volume < 10:
                        continue

                    # Рассчитываем метрики
                    potential_profit = median_price - current_price
                    potential_profit_percent = (potential_profit / current_price) * 100
                    price_volatility = ((median_price - lowest_price) / lowest_price) * 100

                    # Оценка стабильности предмета
                    stability_score = volume * (1 + (sell_listings / 100))  # Больше объем и листингов - стабильнее

                    # Проверяем критерии выгодности
                    if (potential_profit_percent >= min_profit_percent and 
                        price_volatility >= 5 and 
                        stability_score >= 50):  # Минимальный порог стабильности

                        profitable_items.append({
                            'name': name,
                            'current_price': current_price,
                            'median_price': median_price,
                            'lowest_price': lowest_price,
                            'profit_percent': potential_profit_percent,
                            'volatility': price_volatility,
                            'volume': volume,
                            'sell_listings': sell_listings,
                            'stability_score': stability_score
                        })

                except Exception as e:
                    continue

                processed_items += 1
                if processed_items >= max_items:
                    break

            start += batch_size
            time.sleep(0.5)  # Задержка между запросами

        # Сортируем по комплексному показателю: прибыль * стабильность
        profitable_items.sort(
            key=lambda x: (x['profit_percent'] * x['stability_score'], x['volume']), 
            reverse=True
        )
        return profitable_items