from typing import Optional, Tuple
import re

from config.constants import DAY_TO_COLUMN, TIME_TO_ROW

def get_cell_address(day: str, time_slot: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Определяет адрес ячейки по дню и времени
    Возвращает (адрес_ячейки, строка) или (None, None) при ошибке
    """
    column = DAY_TO_COLUMN.get(day)
    row = TIME_TO_ROW.get(time_slot)
    
    if not column or not row:
        return None, None
    
    return f"{column}{row}", row

def cell_to_indices(cell_address: str) -> Tuple[int, int]:
    """
    Преобразует адрес 'B2' в индексы массива (row_idx, col_idx).
    Excel: B2 (Row 2, Col 2) -> Python List: [1][1] (0-based)
    """
    match = re.match(r"([A-Z]+)(\d+)", cell_address)
    if not match:
        raise ValueError(f"Invalid cell address: {cell_address}")
    
    col_str, row_str = match.groups()
    
    # Преобразуем буквы колонки в индекс (A=0, B=1...)
    col_idx = 0
    for char in col_str:
        col_idx = col_idx * 26 + (ord(char) - ord('A'))
        
    # Преобразуем строку (1-based -> 0-based)
    row_idx = int(row_str) - 1
    
    return row_idx, col_idx

def get_human_readable_slot(cell_address: str) -> str:
    """
    Превращает 'B2' в 'Пн 8:00-9:00'
    """
    # Инвертируем маппинги для поиска
    col_to_day = {v: k for k, v in DAY_TO_COLUMN.items()}
    row_to_time = {v: k for k, v in TIME_TO_ROW.items()}
    
    match = re.match(r"([A-Z]+)(\d+)", cell_address)
    if not match:
        return cell_address
        
    col_str, row_str = match.groups()
    row_int = int(row_str)
    
    day = col_to_day.get(col_str, "???")
    time_slot = row_to_time.get(row_int, "??:??")
    
    return f"{day} {time_slot}"