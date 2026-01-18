import json
import os
import logging
from typing import Dict, Optional, List

from utils.date_helpers import is_date_expired, parse_cell_content
from utils.helpers import cell_to_indices

logger = logging.getLogger(__name__)

class UserStorage:
    def __init__(self, filename: str = "users_data.json"):
        self.filename = filename
        self._data = {
            "users": {},      # { "user_id": { "name": "...", "points": {"B2": "19.01"} } }
            "global_map": {}  # { "B2": { "user_id": "...", "date": "19.01" } }
        }
        self._load_from_file()

    def _load_from_file(self):
        """Загружает данные из JSON файла при старте."""
        if not os.path.exists(self.filename):
            self._users = {}
            return

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                
                # Проверка структуры (Миграция)
                if "users" in raw_data and "global_map" in raw_data:
                    self._data = raw_data
                else:
                    # Если старый формат (где корень — это пользователи)
                    logger.info("Обнаружен старый формат базы. Миграция...")
                    self._data["users"] = raw_data
                    self._data["global_map"] = {}
                    # Инициализируем points для старых пользователей
                    for u_id in self._data["users"]:
                        if "points" not in self._data["users"][u_id]:
                            self._data["users"][u_id]["points"] = {}
                    self._save_to_file()
                    
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка при загрузке базы данных: {e}")
            self._data = {"users": {}, "global_map": {}}

    def _save_to_file(self):
        """Сохраняет текущее состояние базы в файл."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            logger.error(f"Ошибка при сохранении базы данных: {e}")

    # --- Методы работы с пользователями ---

    def user_exists(self, user_id: int) -> bool:
        """Проверяет наличие пользователя в базе."""
        return str(user_id) in self._data["users"]

    def add_user(self, user_id: int):
        str_id = str(user_id)
        if str_id not in self._data["users"]:
            self._data["users"][str_id] = {
                "name": None,
                "points": {}
            }
            self._save_to_file()

    def get_user(self, user_id: int) -> Optional[dict]:
        """Возвращает данные пользователя."""
        return self._data["users"].get(str(user_id))

    def get_users_count(self) -> int:
        """Возвращает количество пользователей."""
        return len(self._data["users"])

    def is_name_taken(self, name: str) -> bool:
        """Проверяет, занято ли имя кем-то из пользователей."""
        # Приводим к нижнему регистру для сравнения, чтобы 'Иван' и 'иван' считались одним именем
        target_name = name.lower()
        for user_data in self._data["users"].values():
            existing_name = user_data.get("name")
            if existing_name and existing_name.lower() == target_name:
                return True
        return False

    def set_user_name(self, user_id: int, name: str):
        """Устанавливает имя пользователю."""
        str_id = str(user_id)
        if str_id in self._data["users"]:
            self._data["users"][str_id]["name"] = name
            self._save_to_file()

    # --- Методы работы с записями (Bookings) ---

    def add_booking(self, user_id: int, cell_address: str, date: str):
        """
        Добавляет запись:
        1. В global_map (чтобы знать, чья ячейка)
        2. В points пользователя (чтобы он видел свои записи)
        """
        str_id = str(user_id)
        if str_id not in self._data["users"]:
            self.add_user(user_id)

        # Добавляем в глобальную карту
        self._data["global_map"][cell_address] = {
            "user_id": str_id,
            "date": date
        }

        # Добавляем пользователю
        self._data["users"][str_id]["points"][cell_address] = date
        
        self._save_to_file()
        logger.info(f"Booking added: User {user_id}, Cell {cell_address}, Date {date}")

    def remove_booking(self, cell_address: str):
        """Удаляет запись по адресу ячейки у владельца и из карты."""
        if cell_address not in self._data["global_map"]:
            return

        booking_info = self._data["global_map"][cell_address]
        user_id = booking_info["user_id"]

        # Удаляем из глобальной карты
        del self._data["global_map"][cell_address]

        # Удаляем у пользователя
        if user_id in self._data["users"]:
            if cell_address in self._data["users"][user_id]["points"]:
                del self._data["users"][user_id]["points"][cell_address]

        self._save_to_file()
        logger.info(f"Booking removed: Cell {cell_address}, User {user_id}")

    def get_owner_by_cell(self, cell_address: str) -> Optional[str]:
        """Возвращает user_id владельца записи в ячейке."""
        booking = self._data["global_map"].get(cell_address)
        if booking:
            return booking["user_id"]
        return None
    
    def get_user_bookings(self, user_id: int) -> Dict[str, str]:
        """Возвращает словарь {ячейка: дата} для пользователя."""
        str_id = str(user_id)
        if str_id in self._data["users"]:
            return self._data["users"][str_id].get("points", {})
        return {}

    def sync_user_bookings(self, user_id: int, table_data: List[List[str]]) -> Dict[str, str]:
        """
        Проверяет записи пользователя на актуальность.
        Удаляет просроченные и 'призрачные' записи.
        Возвращает актуальный словарь {ячейка: дата}.
        """
        str_id = str(user_id)
        if str_id not in self._data["users"]:
            return {}

        user_points = self._data["users"][str_id].get("points", {}).copy() # Копия для итерации
        user_name = self._data["users"][str_id].get("name")
        
        cells_to_remove = []

        for cell_address, date_str in user_points.items():
            # 1. Проверка даты (Expired)
            if is_date_expired(date_str):
                cells_to_remove.append(cell_address)
                continue

            # 2. Проверка соответствия таблице (Ghost Booking)
            if not table_data:
                # Если таблица почему-то пуста, лучше ничего не удалять, чтобы не поломать данные при сбое API
                continue
                
            try:
                row_idx, col_idx = cell_to_indices(cell_address)
                
                # Проверка выхода за границы
                if row_idx >= len(table_data) or col_idx >= len(table_data[row_idx]):
                    # Ячейка за пределами таблицы? Считаем, что её очистили.
                    cells_to_remove.append(cell_address)
                    continue

                cell_value = table_data[row_idx][col_idx]
                
                # Если ячейка пуста в таблице -> Ghost
                if not cell_value or not cell_value.strip():
                    cells_to_remove.append(cell_address)
                    continue
                
                # Если в ячейке другое имя -> Ghost
                parsed = parse_cell_content(cell_value)
                if parsed and parsed.get("name"):
                    # Сравниваем имена (без учета регистра)
                    if user_name and parsed["name"].lower() != user_name.lower():
                        cells_to_remove.append(cell_address)
                        continue
                else:
                    # Если там мусор, который нельзя распарсить -> удаляем из брони пользователя
                    cells_to_remove.append(cell_address)

            except Exception as e:
                logger.error(f"Error syncing cell {cell_address}: {e}")
                continue

        # Удаляем накопленное
        for cell in cells_to_remove:
            self.remove_booking(cell)
            
        # Возвращаем актуальное состояние
        return self._data["users"][str_id].get("points", {})

# Глобальный экземпляр
user_storage = UserStorage()