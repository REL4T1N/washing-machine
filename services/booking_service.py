import asyncio
import time
import logging
from collections import defaultdict
from typing import List, Tuple

from config.constants import DAY_TO_COLUMN, TIME_TO_ROW, TIME_SLOTS, GS_DATA_RANGE

from services.google_sheets import GoogleSheetsService
from services.storage import UserStorage

from utils.helpers import get_cell_address
from utils.date_helpers import is_cell_available_for_date, create_booking_record

logger = logging.getLogger(__name__)

class BookingService:
    """
    Сервис бизнес-логики бронирования.
    
    Обеспечивает:
    1. Потокобезопасный доступ к данным таблицы (asyncio.Lock).
    2. Кэширование данных Google Sheets для снижения количества API-запросов.
    3. Атомарность операций бронирования (предотвращение двойной записи).
    """

    def __init__(
        self,
        gs_service: GoogleSheetsService,
        user_storage: UserStorage,
        sheet_name: str,
        cache_ttl: int = 60,
        lock_timeout: int = 10,
    ): 
        """
        Args:
            gs_service: Инстанс сервиса Google Sheets.
            user_storage: Локальное хранилище пользователей.
            sheet_name: Имя листа в таблице.
            cache_ttl: Время жизни кэша таблицы в секундах.
            lock_timeout: Максимальное время ожидания блокировки ячейки.
        """
        self.gs = gs_service
        self.storage = user_storage
        self.sheet_name = sheet_name

        self._cache_data: List[List[str]] | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl = cache_ttl
        self._cache_lock = asyncio.Lock()

        self._cell_locks = defaultdict(asyncio.Lock)
        self._lock_timeout = lock_timeout

    async def get_table_data(self, force_refresh: bool = False) -> List[List[str]]:
        """Получает данные таблицы, используя потокобезопасный кэш.
        
        Args:
            force_refresh: Если True, принудительно запрашивает данные из API.

        Returns:
            List[List[str]]: Двумерный массив строк из таблицы.
        """
        current_time = time.time()
        if not force_refresh and self._cache_data and (current_time - self._cache_timestamp < self._cache_ttl):
            return self._cache_data

        async with self._cache_lock:
            # Повторная проверка внутри лока на случай, если другой поток уже обновил кэш
            current_time = time.time()
            if not force_refresh and self._cache_data and (current_time - self._cache_timestamp < self._cache_ttl):
                return self._cache_data

            logger.info("🔄 Обновление кэша таблицы из Google Sheets...")
            try:
                data = await self.gs.get_data(self.sheet_name, GS_DATA_RANGE)
                self._cache_data = data if data else []
                self._cache_timestamp = current_time
                logger.info(f"✅ Кэш обновлен, строк: {len(self._cache_data)}")
            except Exception as e:
                logger.error(f"❌ Ошибка обновления кэша: {e}. Будут использованы старые данные, если они есть.")
            
            return self._cache_data or []

    async def invalidate_cache(self) -> None:
        """Принудительно сбрасывает кэш."""
        async with self._cache_lock:
            self._cache_data = None
            self._cache_timestamp = 0
            logger.info("🗑️ Кэш таблицы сброшен.")

    async def _is_cell_free(self, cell_address: str, target_date: str) -> Tuple[bool, str, str]:
        """Проверяет, свободна ли ячейка, используя данные из Google Sheets (не из кэша)."""
        try:
            result = await self.gs.get_data(self.sheet_name, cell_address)
            value = result[0][0].strip() if result and result[0] and result[0][0] else ""

            if not value:
                return True, "", ""  # Ячейка пуста

            is_available, error_msg = is_cell_available_for_date(value, target_date)
            if not is_available:
                return False, value, error_msg
            
            return True, "", ""
        except Exception as e:
            logger.error(f"Ошибка проверки ячейки {cell_address}: {e}")
            return False, "", f"Ошибка проверки ячейки: {e}"

    async def book_slot(self, user_id: int, day: str, time_slot: str, target_date: str) -> Tuple[bool, str]:
        """
        Бронирует слот для пользователя.
        
        Логика:
        1. Проверяет наличие имени пользователя в базе.
        2. Захватывает Lock конкретной ячейки.
        3. Проверяет ячейку в таблице (свежий запрос).
        4. Делает запись в Google Sheets.
        5. Дублирует запись в локальный UserStorage.
        6. Сбрасывает общий кэш.

        Returns:
            Tuple[bool, str]: (Успех операции, Сообщение об ошибке или пустая строка).
        """
        cell_address, _ = get_cell_address(day, time_slot)
        if not cell_address:
            return False, "Неверный день или временной слот."

        user = self.storage.get_user(user_id)
        if not user or not user.get('name'):
            return False, "Не удалось получить ваше имя. Установите его командой /name."
        
        lock = self._cell_locks[cell_address]
        try:
            await asyncio.wait_for(lock.acquire(), timeout=self._lock_timeout)
        except asyncio.TimeoutError:
            return False, "⏳ Слот сейчас занят другим пользователем. Попробуйте через мгновение."

        try:
            is_free, current_value, error_msg = await self._is_cell_free(cell_address, target_date)
            if not is_free:
                return False, error_msg or f"❌ Ячейка уже занята: <b>{current_value}</b>"

            booking_record = create_booking_record(user['name'], target_date)
            success = await self.gs.write_value(self.sheet_name, cell_address, booking_record)
            if not success:
                return False, "Ошибка записи в Google таблицу."

            await self.storage.add_booking(user_id, cell_address, target_date)
            await self.invalidate_cache()
            
            return True, ""
        finally:
            lock.release()

    async def delete_booking(self, cell_address: str, user_id: int) -> Tuple[bool, str]:
        """Удаляет бронирование."""
        owner_id = self.storage.get_owner_by_cell(cell_address)
        if owner_id and str(owner_id) != str(user_id):
            return False, "❌ Это не ваша запись!"

        lock = self._cell_locks[cell_address]
        try:
            await asyncio.wait_for(lock.acquire(), timeout=self._lock_timeout)
        except asyncio.TimeoutError:
            return False, "⏳ Система занята, попробуйте через пару секунд."

        try:
            success = await self.gs.clear_cell(self.sheet_name, cell_address)
            if success:
                await self.storage.remove_booking(cell_address)
                await self.invalidate_cache()
                return True, ""
            else:
                return False, "Ошибка связи с Google Sheets."
        finally:
            lock.release()

    async def get_free_slots_for_day(self, day: str, target_date: str) -> List[str]:
        """Анализирует таблицу и возвращает список свободных слотов на определенный день, используя кэш."""
        column_idx_map = {
            "Пн": 1,  # Колонка B (индекс 1)
            "Вт": 3,  # Колонка D (индекс 3)
            "Ср": 5,  # Колонка F (индекс 5)
            "Чт": 7,  # Колонка H (индекс 7)
            "Пт": 9,  # Колонка J (индекс 9)
            "Сб": 11, # Колонка L (индекс 11)
            "Вс": 13  # Колонка N (индекс 13)
        }
        col_idx = column_idx_map.get(day)
        if col_idx is None:
            return []

        table_data = await self.get_table_data()
        if not table_data:
            return [time_slot for time_slot, _ in TIME_SLOTS]

        free_slots = []
        for time_slot, _ in TIME_SLOTS:
            row_idx = TIME_TO_ROW.get(time_slot)
            if not row_idx:
                continue
            
            data_row_idx = row_idx - 1
            
            cell_value = ""
            if data_row_idx < len(table_data) and col_idx < len(table_data[data_row_idx]):
                cell_value = table_data[data_row_idx][col_idx].strip()

            if not cell_value or is_cell_available_for_date(cell_value, target_date)[0]:
                free_slots.append(time_slot)
        
        return free_slots
