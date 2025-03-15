import requests
import time
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

class SteamMarketAPI:
    BASE_URL = "https://steamcommunity.com/market/priceoverview/"
    HISTORY_URL = "https://steamcommunity.com/market/pricehistory/"

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
        except requests.RequestException as e:
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

    def search_items(self, query: str) -> list:
        """Поиск предметов по названию"""
        try:
            params = {
                'appid': '730',
                'query': query,
                'count': 100  # Увеличим количество результатов
            }
            response = self.session.get(
                "https://steamcommunity.com/market/search/render/",
                params=params
            )
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.RequestException:
            return []

    def find_profitable_items(self, min_profit_percent: float = 10.0) -> List[Dict]:
        """Поиск выгодных предметов для перепродажи"""
        profitable_items = []

        # Получаем популярные предметы
        popular_items = self.search_items("")  # Пустой запрос для получения популярных предметов

        for item in popular_items:
            try:
                name = item['name']
                current_price = float(item.get('price', '0').replace(',', '.').replace('₽', '').strip())

                # Получаем историю цен
                history_data = self.get_price_history(name)
                if not history_data or not history_data.get('prices'):
                    continue

                # Анализируем историю цен
                prices = [float(price[1]) for price in history_data['prices']]
                if not prices:
                    continue

                min_price = min(prices[-30:]) if len(prices) >= 30 else min(prices)  # За последние 30 дней
                avg_price = sum(prices[-30:]) / min(30, len(prices))

                # Рассчитываем потенциальную прибыль
                potential_profit_percent = ((avg_price - current_price) / current_price) * 100

                if potential_profit_percent >= min_profit_percent:
                    profitable_items.append({
                        'name': name,
                        'current_price': current_price,
                        'avg_price': avg_price,
                        'min_price': min_price,
                        'profit_percent': potential_profit_percent,
                        'volume': item.get('volume', 0)
                    })

            except (ValueError, KeyError, ZeroDivisionError):
                continue

        # Сортируем по потенциальной прибыли
        profitable_items.sort(key=lambda x: x['profit_percent'], reverse=True)
        return profitable_items