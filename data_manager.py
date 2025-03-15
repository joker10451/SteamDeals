import json
import os
from typing import List, Dict
from datetime import datetime

class DataManager:
    def __init__(self, filename: str = "watched_items.json"):
        self.filename = filename
        self.watched_items = self.load_data()

    def load_data(self) -> Dict:
        """Загрузка данных из файла"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_data(self):
        """Сохранение данных в файл"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.watched_items, f, ensure_ascii=False, indent=2)

    def add_watched_item(self, item_name: str, current_price: float):
        """Добавление предмета в отслеживаемые"""
        if item_name not in self.watched_items:
            self.watched_items[item_name] = {
                'added_date': datetime.now().isoformat(),
                'initial_price': current_price,
                'price_history': [(datetime.now().isoformat(), current_price)]
            }
            self.save_data()

    def remove_watched_item(self, item_name: str):
        """Удаление предмета из отслеживаемых"""
        if item_name in self.watched_items:
            del self.watched_items[item_name]
            self.save_data()

    def update_price(self, item_name: str, new_price: float):
        """Обновление цены предмета"""
        if item_name in self.watched_items:
            self.watched_items[item_name]['price_history'].append(
                (datetime.now().isoformat(), new_price)
            )
            self.save_data()

    def get_watched_items(self) -> List[str]:
        """Получение списка отслеживаемых предметов"""
        return list(self.watched_items.keys())
