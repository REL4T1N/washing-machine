from typing import Optional, Tuple

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