import requests
import time
from typing import Dict, Optional, Tuple

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
                'count': 10
            }
            response = self.session.get(
                "https://steamcommunity.com/market/search/render/",
                params=params
            )
            response.raise_for_status()
            return response.json().get('results', [])
        except requests.RequestException:
            return []
