import requests
import time
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta

class SteamMarketAPI:
    BASE_URL = "https://steamcommunity.com/market/priceoverview/"
    SEARCH_URL = "https://steamcommunity.com/market/search/render/"

    def __init__(self):
        self.session = requests.Session()
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour cache
        self.max_retries = 3
        self.retry_delay = 2

    def _parse_price(self, price_str: str) -> float:
        """Парсинг цены из строки"""
        try:
            # Удаляем все нечисловые символы, кроме точки и запятой
            price_str = ''.join(c for c in price_str if c.isdigit() or c in '.,')
            # Заменяем запятую на точку и конвертируем в float
            return float(price_str.replace(',', '.'))
        except (ValueError, AttributeError):
            return 0.0

    def _make_request_with_retry(self, url: str, params: Dict) -> Optional[Dict]:
        """Выполнение запроса с повторными попытками при ошибках"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as e:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(self.retry_delay * (attempt + 1))
        return None

    def get_item_price(self, item_name: str) -> Optional[Dict]:
        """Получение текущей цены предмета"""
        params = {
            'appid': '730',  # CS:GO
            'currency': '5',  # RUB
            'market_hash_name': item_name
        }
        return self._make_request_with_retry(self.BASE_URL, params)

    def search_items(self, query: str, start: int = 0, count: int = 100) -> List[Dict]:
        """Поиск предметов по названию с пагинацией"""
        params = {
            'appid': '730',  # CS:GO
            'query': query,
            'start': start,
            'count': count,
            'search_descriptions': 0,
            'sort_column': 'price',  # Сортировка по цене
            'sort_dir': 'asc',       # По возрастанию
            'norender': 1
        }
        result = self._make_request_with_retry(self.SEARCH_URL, params)
        return result.get('results', []) if result else []

    def find_profitable_items(self, min_profit_percent: float = 5.0, max_items: int = 500) -> List[Dict]:
        """Поиск выгодных предметов для перепродажи"""
        profitable_items = []
        processed_items = 0
        start = 0
        batch_size = 100

        categories = ['', 'Knife', 'Gloves', 'Pistol', 'Rifle']  # Различные категории предметов

        for category in categories:
            start = 0
            while processed_items < max_items:
                items = self.search_items(category, start, batch_size)
                if not items:
                    break

                for item in items:
                    try:
                        name = item['name']
                        sell_listings = int(item.get('sell_listings', 0))

                        # Более мягкие условия для редких предметов
                        min_listings = 3 if 'Knife' in name or 'Gloves' in name else 5

                        if sell_listings < min_listings:
                            continue

                        # Парсим текущую цену
                        current_price = self._parse_price(item.get('sell_price_text', item.get('price', '0')))
                        if current_price <= 0:
                            continue

                        # Получаем рыночные данные
                        market_data = self.get_item_price(name)
                        if not market_data:
                            continue

                        # Парсим цены
                        lowest_price = self._parse_price(market_data.get('lowest_price', '0'))
                        median_price = self._parse_price(market_data.get('median_price', '0'))
                        volume = int(market_data.get('volume', '0'))

                        if lowest_price <= 0 or median_price <= 0:
                            continue

                        # Рассчитываем метрики
                        potential_profit = median_price - current_price
                        potential_profit_percent = (potential_profit / current_price) * 100
                        price_volatility = ((median_price - lowest_price) / lowest_price) * 100

                        # Адаптивная оценка стабильности в зависимости от категории
                        if 'Knife' in name or 'Gloves' in name:
                            # Для дорогих предметов требования ниже
                            stability_score = volume * 2 + sell_listings
                            min_stability = 10
                        else:
                            # Для обычных предметов
                            stability_score = volume + (sell_listings / 2)
                            min_stability = 20

                        if (potential_profit_percent >= min_profit_percent and 
                            price_volatility >= 3 and 
                            stability_score >= min_stability):

                            profitable_items.append({
                                'name': name,
                                'current_price': current_price,
                                'median_price': median_price,
                                'lowest_price': lowest_price,
                                'profit_percent': potential_profit_percent,
                                'volatility': price_volatility,
                                'volume': volume,
                                'sell_listings': sell_listings,
                                'stability_score': stability_score,
                                'category': 'Rare' if 'Knife' in name or 'Gloves' in name else 'Common'
                            })

                    except Exception as e:
                        continue

                    processed_items += 1
                    if processed_items >= max_items:
                        break

                start += batch_size
                time.sleep(0.5)  # Задержка между запросами

        # Сортируем предметы с учетом категории и прибыльности
        profitable_items.sort(
            key=lambda x: (
                2 if x['category'] == 'Rare' else 1,  # Приоритет редких предметов
                x['profit_percent'] * x['stability_score']
            ),
            reverse=True
        )
        return profitable_items