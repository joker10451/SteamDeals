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

    def get_price_history(self, item_name: str) -> Optional[Dict]:
        """Получение истории цен предмета"""
        cache_key = f"history_{item_name}"

        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_timeout:
                return cached_data

        try:
            params = {
                'appid': '730',  # CS:GO
                'market_hash_name': item_name
            }

            response = self.session.get(self.HISTORY_URL, params=params)
            response.raise_for_status()
            data = response.json()

            self.cache[cache_key] = (data, time.time())
            return data
        except requests.RequestException:
            return None

    def search_items(self, query: str, start: int = 0) -> List[Dict]:
        """Поиск предметов по названию с пагинацией"""
        try:
            params = {
                'appid': '730',
                'query': query,
                'start': start,
                'count': 100,
                'sort_column': 'popular',
                'sort_dir': 'desc'
            }
            response = self.session.get(self.SEARCH_URL, params=params)
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.RequestException:
            return []

    def _parse_price(self, price_str: str) -> float:
        """Парсинг цены из строки"""
        try:
            return float(price_str.replace('₽', '').replace(',', '.').strip())
        except (ValueError, AttributeError):
            return 0.0

    def find_profitable_items(self, min_profit_percent: float = 5.0, max_items: int = 300) -> List[Dict]:
        """Поиск выгодных предметов для перепродажи"""
        profitable_items = []
        processed_items = 0
        start = 0

        while processed_items < max_items:
            # Получаем предметы порциями
            items = self.search_items("", start)
            if not items:
                break

            for item in items:
                try:
                    name = item['name']
                    current_price = self._parse_price(item.get('sell_price_text', item.get('price', '0')))

                    if current_price <= 0:
                        continue

                    # Получаем историю цен
                    history_data = self.get_price_history(name)
                    if not history_data or not history_data.get('prices'):
                        continue

                    # Анализируем историю цен за последние 7 дней
                    prices = []
                    week_ago = datetime.now() - timedelta(days=7)

                    for price_entry in history_data['prices']:
                        try:
                            date = datetime.strptime(price_entry[0], '%b %d %Y %H: +0')
                            if date >= week_ago:
                                prices.append(float(price_entry[1]))
                        except (ValueError, IndexError):
                            continue

                    if not prices:
                        continue

                    avg_price = sum(prices) / len(prices)
                    max_price = max(prices)
                    min_price = min(prices)
                    price_volatility = (max_price - min_price) / min_price * 100

                    # Рассчитываем потенциальную прибыль
                    potential_profit_percent = ((avg_price - current_price) / current_price) * 100

                    # Добавляем предмет, если он соответствует критериям
                    if potential_profit_percent >= min_profit_percent and price_volatility >= 5:
                        profitable_items.append({
                            'name': name,
                            'current_price': current_price,
                            'avg_price': avg_price,
                            'min_price': min_price,
                            'max_price': max_price,
                            'profit_percent': potential_profit_percent,
                            'volatility': price_volatility,
                            'volume': item.get('volume', 0)
                        })

                except Exception as e:
                    continue

                processed_items += 1
                if processed_items >= max_items:
                    break

            start += len(items)
            time.sleep(1)  # Задержка между запросами

        # Сортируем по потенциальной прибыли и волатильности
        profitable_items.sort(key=lambda x: (x['profit_percent'], x['volatility']), reverse=True)
        return profitable_items