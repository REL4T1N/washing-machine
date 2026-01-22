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
    Основной сервис бизнес-логики.
    Управляет кэшем, блокировками и координирует работу с Google Sheets и хранилищем пользователей.
    """

    def __init__(
        self,
        gs_service: GoogleSheetsService,
        user_storage: UserStorage,
        sheet_name: str,
        cache_ttl: int = 60,
        lock_timeout: int = 10,
    ):
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
        """Получает данные таблицы, используя потокобезопасный кэш."""
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

    async def invalidate_cache(self):
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
        """Основной метод для бронирования слота."""
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
        """Возвращает список свободных слотов на определенный день, используя кэш."""
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

# # ============ ГЛОБАЛЬНЫЙ КЭШ ТАБЛИЦЫ ============
# TABLE_CACHE = {
#     'data': None,        # Данные таблицы (список списков)
#     'timestamp': 0,      # Время последнего обновления (timestamp)
#     'ttl': 30,           # Время жизни кэша в секундах
#     'is_fetching': False # Флаг чтобы избежать дублирующих запросов
# }

# async def get_cached_table(force_refresh: bool = False) -> list:
#     """
#     Получает таблицу из кэша или Google Sheets
    
#     Аргументы:
#     - force_refresh: если True, игнорирует кэш и обновляет данные
    
#     Возвращает:
#     - Данные таблицы (список списков) или пустой список при ошибке
#     """
#     global TABLE_CACHE
    
#     current_time = time.time()
    
#     # 1. Проверяем нужно ли обновить кэш
#     should_refresh = (
#         force_refresh or
#         TABLE_CACHE['data'] is None or
#         current_time - TABLE_CACHE['timestamp'] > TABLE_CACHE['ttl']
#     )
    
#     if not should_refresh:
#         # Возвращаем данные из кэша
#         return TABLE_CACHE['data'] or []
    
#     # 2. Если уже кто-то обновляет кэш, ждём
#     if TABLE_CACHE['is_fetching']:
#         # Ждём максимум 5 секунд
#         for _ in range(50):  # 50 × 0.1 = 5 секунд
#             await asyncio.sleep(0.1)
#             if not TABLE_CACHE['is_fetching']:
#                 return TABLE_CACHE['data'] or []
#         # Если не дождались, возвращаем старые данные
#         return TABLE_CACHE['data'] or []
    
#     # 3. Обновляем кэш
#     TABLE_CACHE['is_fetching'] = True
#     try:
#         print("🔄 Загружаю таблицу из Google Sheets...")
#         result = await google_sheets_service.get_data(SHEET_NAME, "A1:N9")
        
#         # Проверяем результат
#         if result and isinstance(result, list):
#             TABLE_CACHE['data'] = result
#             TABLE_CACHE['timestamp'] = current_time
#             print(f"✅ Таблица загружена, строк: {len(result)}")
#         else:
#             print("⚠️ Получены пустые данные")
#             TABLE_CACHE['data'] = []
#             TABLE_CACHE['timestamp'] = current_time
        
#         return TABLE_CACHE['data']
        
#     except Exception as e:
#         print(f"❌ Ошибка загрузки таблицы: {e}")
#         # Возвращаем старые данные если есть
#         return TABLE_CACHE['data'] or []
        
#     finally:
#         TABLE_CACHE['is_fetching'] = False

# def invalidate_table_cache():
#     """
#     Принудительно очищает кэш таблицы
#     Вызывается после записи в таблицу
#     """
#     global TABLE_CACHE
#     TABLE_CACHE['data'] = None
#     TABLE_CACHE['timestamp'] = 0
#     print("🗑️ Кэш таблицы очищен")


# async def write_to_sheet_with_lock(
#     day: str, 
#     time_slot: str, 
#     name: str,  # Добавляем параметр name
#     target_date: str,  # Делаем обязательным
#     booking_record: str = None,  # Опционально: готовая запись
#     tg_id: int = None
# ) -> tuple[bool, str]:
#     """
#     Записывает значение в таблицу с блокировкой и обновляет storage.
#     """
#     try:
#         # Определяем адрес ячейки
#         cell_address, row = get_cell_address(day, time_slot)
        
#         if not cell_address:
#             return False, "Неизвестный день или время"
        
#         # Формируем запись если не предоставлена
#         if not booking_record:
#             booking_record = create_booking_record(name, target_date)
        
#         # Пытаемся получить блокировку
#         lock_acquired = LockService.acquire_lock(cell_address)
#         if not lock_acquired:
#             return False, "❌ Слишком много попыток записи. Попробуйте через 10 секунд."
        
#         try:
#             # Проверяем, свободна ли ячейка для указанной даты
#             is_free, current_value, error_msg = await is_cell_free(cell_address, target_date)
            
#             if not is_free:
#                 if error_msg:
#                     return False, error_msg
#                 else:
#                     return False, f"❌ Ячейка уже занята: <b>{current_value}</b>"
                
            
#             # Записываем значение
#             success = await google_sheets_service.write_value(
#                 sheet_name=SHEET_NAME,
#                 cell=cell_address,
#                 value=booking_record
#             )

#             if success:
#                 if tg_id:
#                     user_storage.add_booking(
#                         user_id=tg_id,
#                         cell_address=cell_address,
#                         date=target_date
#                     )
                
#             elif not success:
#                 return False, "Ошибка записи в таблицу (Google API)"
            
#             return True, ""
            
#         finally:
#             # Всегда освобождаем блокировку
#             LockService.release_lock(cell_address)

#             # ВСЕГДА очищаем кэш после записи!
#             invalidate_table_cache()
            
#     except Exception as e:
#         # При ошибке тоже очищаем кэш
#         invalidate_table_cache()
#         return False, f"Ошибка записи: {str(e)}"
    
# async def is_cell_free(cell_address: str, target_date: str) -> tuple[bool, str, str]:
#     """
#     Проверяет, свободна ли ячейка для указанной даты
#     target_date теперь обязательный параметр
    
#     Важно: при любой ошибке считаем ячейку занятой (безопасный подход)
#     """
#     try:
#         # Читаем ячейку
#         result = await google_sheets_service.get_data(SHEET_NAME, cell_address)
        
#         if not result or not result[0]:
#             return True, "", ""  # Пустая ячейка
        
#         value = result[0][0] if result[0] else ""
#         if not value or not value.strip():
#             return True, "", ""  # Пустая ячейка
        
#         # Проверяем доступность для указанной даты
#         is_available, error_msg = is_cell_available_for_date(value.strip(), target_date)
        
#         if not is_available:
#             return False, value.strip(), error_msg
        
#         # Можно перезаписать (даты разные)
#         return True, "", ""
        
#     except Exception as e:
#         return False, "", f"Ошибка проверки ячейки: {str(e)}"

# async def get_free_times_for_day(day: str, target_date: str = None) -> list[str]:
#     """
#     Получает список СВОБОДНЫХ времен для указанного дня и даты
#     Работает с кэшированной таблицей (не делает запросов к API)
#     """
#     try:
#         column = DAY_TO_COLUMN.get(day)
#         if not column:
#             print(f"⚠️ Неизвестный день: {day}")
#             return []
        
#         # 1. Получаем таблицу из кэша (ОДИН "запрос" в память)
#         table_data = await get_cached_table()
        
#         if not table_data or len(table_data) < 2:
#             print(f"⚠️ Пустая таблица в кэше для дня {day}")
#             return [time_slot for time_slot, _ in TIME_SLOTS]
        
#         # 2. Определяем индекс колонки для этого дня
#         # Маппинг: день → индекс в данных таблицы (0-based)
#         day_column_indices = {
#             "Пн": 1,  # Колонка B (индекс 1)
#             "Вт": 3,  # Колонка D (индекс 3)
#             "Ср": 5,  # Колонка F (индекс 5)
#             "Чт": 7,  # Колонка H (индекс 7)
#             "Пт": 9,  # Колонка J (индекс 9)
#             "Сб": 11, # Колонка L (индекс 11)
#             "Вс": 13  # Колонка N (индекс 13)
#         }
        
#         column_idx = day_column_indices.get(day)
#         if column_idx is None:
#             print(f"⚠️ Не найден индекс колонки для дня {day}")
#             return []
        
#         # Проверяем что колонка существует в данных
#         if column_idx >= len(table_data[0]):
#             print(f"⚠️ Колонка {column_idx} выходит за пределы таблицы")
#             return []

#         free_times = []
        
#         # 3. Проходим по всем временным слотам
#         for time_slot, _ in TIME_SLOTS:
#             row_idx = TIME_TO_ROW.get(time_slot)
#             if not row_idx:
#                 print(f"⚠️ Неизвестный временной слот: {time_slot}")
#                 continue
            
#             # row_idx: 2-9 (1-based), в данных: 1-8 (0-based)
#             data_row_idx = row_idx - 1
            
#             # Проверяем что строка существует
#             if data_row_idx >= len(table_data):
#                 print(f"⚠️ Строка {data_row_idx} выходит за пределы таблицы")
#                 continue
            
#             row_data = table_data[data_row_idx]
            
#             # Получаем значение ячейки
#             if column_idx < len(row_data):
#                 cell_value = row_data[column_idx] if row_data[column_idx] else ""
#             else:
#                 cell_value = ""
            
#             cell_value = cell_value.strip() if cell_value else ""
            
#             # 4. Проверяем доступность ячейки
#             if not cell_value:
#                 # Пустая ячейка - свободна
#                 free_times.append(time_slot)
#             else:
#                 # Есть запись - проверяем дату
#                 is_available, _ = is_cell_available_for_date(cell_value, target_date)
#                 if is_available:
#                     free_times.append(time_slot)
#                 # else: занято на эту дату - не добавляем
        
#         print(f"✅ Для дня {day} ({target_date}) найдено свободных слотов: {len(free_times)}")
#         return free_times
        
#     except Exception as e:
#         print(f"Ошибка при получении свободных времен: {e}")
#         return [] # При общей ошибке - пустой список
    

# async def delete_booking(cell_address: str, user_id: int) -> tuple[bool, str]:
#     """
#     Удаляет бронь:
#     1. Блокирует ячейку
#     2. Очищает в Google Sheets (ставит пустую строку)
#     3. Удаляет из user_storage
#     """
#     try:
#         # Проверяем владельца (на всякий случай)
#         owner_id = user_storage.get_owner_by_cell(cell_address)
#         if owner_id and str(owner_id) != str(user_id):
#              return False, "❌ Это не ваша запись!"

#         lock_acquired = LockService.acquire_lock(cell_address)
#         if not lock_acquired:
#             return False, "⏳ Система занята, попробуйте через пару секунд"

#         try:
#             # Пишем пустую строку в Google Sheets
#             success = await google_sheets_service.write_value(
#                 sheet_name=SHEET_NAME,
#                 cell=cell_address,
#                 value="" 
#             )

#             if success:
#                 user_storage.remove_booking(cell_address)
#                 invalidate_table_cache() # Сбрасываем кэш
#                 return True, ""
#             else:
#                 return False, "Ошибка связи с Google Sheets"

#         finally:
#             LockService.release_lock(cell_address)

#     except Exception as e:
#         invalidate_table_cache()
#         return False, f"Ошибка удаления: {e}"