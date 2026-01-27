import asyncio
import json
import logging
import os
from typing import Dict, Optional, List

from utils.date_helpers import is_date_expired, parse_cell_content
from utils.helpers import cell_to_indices

logger = logging.getLogger(__name__)

class UserStorage:
    """
    Асинхронное файловое хранилище для данных пользователей и бронирований.
    
    Использует JSON для персистентности и asyncio.Lock для потокобезопасности.
    """

    def __init__(self, filename: str = "users_data.json"):
        """
        Args:
            filename: Путь к JSON-файлу хранилища.
        """
        self.filename = filename
        self._lock = asyncio.Lock()
        self._data = {
            "users": {},      # { "user_id": { "name": str, "points": { "cell": "date" } } }
            "global_map": {}  # { "cell_address": { "user_id": str, "date": str } }
        }

    async def load(self) -> None:
        """
        Асинхронно загружает данные из файла.
        Должна вызываться один раз при старте приложения.
        """
        async with self._lock:
            if not os.path.exists(self.filename):
                logger.warning(f"Файл {self.filename} не найден. Будет создан новый.")
                return

            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._load_sync)
                logger.info(f"✅ Данные пользователей успешно загружены из {self.filename}.")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"❌ Ошибка загрузки данных из {self.filename}: {e}")

    def _load_sync(self) -> None:
        """Синхронная часть загрузки данных."""
        with open(self.filename, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            # Простая миграция со старого формата
            if "users" in raw_data and "global_map" in raw_data:
                self._data = raw_data
            else:
                logger.info("Обнаружен старый формат базы. Проводится миграция...")
                self._data["users"] = raw_data
                self._data["global_map"] = {}
                for u_id in self._data["users"]:
                    if "points" not in self._data["users"][u_id]:
                        self._data["users"][u_id]["points"] = {}

    async def _save(self) -> None:
        """Асинхронно и безопасно сохраняет данные в файл."""
        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._save_sync)

    def _save_sync(self) -> None:
        """Синхронная часть сохранения данных."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            logger.error(f"❌ Ошибка сохранения данных в {self.filename}: {e}")


    # --- Методы работы с пользователями (только читающие) ---

    def user_exists(self, user_id: int) -> bool:
        """Проверяет наличие пользователя в базе."""
        return str(user_id) in self._data["users"]
    
    def get_user(self, user_id: int) -> Optional[dict]:
        """Возвращает данные пользователя."""
        return self._data["users"].get(str(user_id))
    
    def get_users_count(self) -> int:
        """Возвращает количество пользователей."""
        return len(self._data["users"])
    
    def is_name_taken(self, name: str) -> bool:
        """Проверяет, занято ли имя кем-то из пользователей."""
        target_name = name.lower()
        for user_data in self._data["users"].values():
            existing_name = user_data.get("name")
            if existing_name and existing_name.lower() == target_name:
                return True
        return False

    # --- Методы работы с пользователями (читающие и пишущие) ---

    async def add_user(self, user_id: int) -> None:
        str_id = str(user_id)
        if str_id not in self._data["users"]:
            self._data["users"][str_id] = {
                "name": None,
                "points": {}
            }
            await self._save()

    async def set_user_name(self, user_id: int, name: str) -> None:
        """Устанавливает имя пользователю."""
        str_id = str(user_id)
        if str_id in self._data["users"]:
            self._data["users"][str_id]["name"] = name
            await self._save()

    # --- Методы работы с записями (Bookings) (только читающие) ---

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

    # --- Методы работы с записями (Bookings) (читающие и пишущие) ---

    async def add_booking(self, user_id: int, cell_address: str, date: str) -> None:
        """
        Добавляет запись:
        1. В global_map (чтобы знать, чья ячейка)
        2. В points пользователя (чтобы он видел свои записи)
        """
        str_id = str(user_id)
        if str_id not in self._data["users"]:
            await self.add_user(user_id)

        # Добавляем в глобальную карту
        self._data["global_map"][cell_address] = {
            "user_id": str_id,
            "date": date
        }

        # Добавляем пользователю
        self._data["users"][str_id]["points"][cell_address] = date
        
        await self._save()
        logger.info(f"Запись добавлена: User {user_id}, Cell {cell_address}, Date {date}")

    async def remove_booking(self, cell_address: str) -> None:
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

        await self._save()
        logger.info(f"Запись удалена: Cell {cell_address}, User {user_id}")

    async def sync_user_bookings(self, user_id: int, table_data: List[List[str]]) -> Dict[str, str]:
        """
        Синхронизирует локальные данные пользователя с состоянием Google Таблицы.
        Удаляет просроченные записи или те, что были изменены в таблице вручную.
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
            try:
                row_idx, col_idx = cell_to_indices(cell_address)
                
                # Проверка выхода за границы
                if row_idx >= len(table_data) or col_idx >= len(table_data[row_idx]):
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
                    if user_name and parsed["name"].lower() != user_name.lower():
                        cells_to_remove.append(cell_address)
                        continue
                else:
                    # Если мусор, который нельзя распарсить -> удаляем из брони пользователя
                    cells_to_remove.append(cell_address)

            except Exception as e:
                logger.warning(f"Ошибка при синхронизации ячейки {cell_address}: {e}")
                continue

        # Удаление накопленного
        if cells_to_remove:
            logger.info(f"Для пользователя {user_id} будут удалены призрачные записи: {cells_to_remove}")
            for cell in cells_to_remove:
                await self.remove_booking(cell)
            
        # Актуальное состояние
        return self._data["users"][str_id].get("points", {})
