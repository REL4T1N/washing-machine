from typing import List
from config.constants import DAYS_OF_WEEK
from utils.date_helpers import parse_cell_content, get_date_for_day


def split_message(text: str, max_length: int = 4000) -> List[str]:
    """Разбивает длинное сообщение на части"""
    messages = []
    while len(text) > max_length:
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
            
        messages.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    
    if text:
        messages.append(text)
    
    return messages

def format_washing_schedule_simple(data: List[List[str]], table_link: str) -> str:
    """
    Преобразует данные из Google Sheets в красивое текстовое расписание.
    Сравнивает даты в ячейках с текущей неделей, чтобы скрыть записи за другие недели.
    """
    if len(data) < 2:
        return "📭 Таблица пуста"
    
    lines = [f"📅 <b>Расписание использования стиральной машины согласно {table_link}</b>\n"]
    
    # Даты для текущей недели
    current_week_dates = {day: get_date_for_day(day) for day in DAYS_OF_WEEK}
    
    for day_idx, day_name in enumerate(DAYS_OF_WEEK):
        name_col_idx = day_idx * 2 + 1
        
        if day_idx * 2 >= len(data[0]):
            continue
        
        day_lines = [f"\n<b>{day_name}</b>", "─" * 20]
        
        # Дата текущего дня недели в этой неделе
        current_date = current_week_dates.get(day_name)
        
        for time_row_idx in range(1, min(9, len(data))):
            time_slot = data[time_row_idx][0] if data[time_row_idx] else ""
            
            booking = "свободно"
            if (len(data[time_row_idx]) > name_col_idx and 
                data[time_row_idx][name_col_idx] and 
                data[time_row_idx][name_col_idx].strip()):
                
                cell_value = data[time_row_idx][name_col_idx].strip()
                
                # Парсинг записи
                parsed = parse_cell_content(cell_value)
                
                if parsed and parsed.get('date'):
                    # Актуальна ли запись для этой недели
                    if current_date and parsed['date'] == current_date:
                        # Запись на эту неделю - показываем
                        booking = cell_value
                    else:
                        # Запись на другую неделю - показываем как свободно
                        booking = "свободно"
                else:
                    # Не удалось распарсить или нет даты
                    booking = cell_value
            else:
                booking = "свободно"
            
            if time_slot:
                status = "🔴" if booking != "свободно" else "🟢"
                day_lines.append(f"{status} <b>{time_slot}</b>: {booking}")
        
        lines.extend(day_lines)
    
    lines.append("\n📆 <i>Актуально на текущую неделю</i>")
    
    return "\n".join(lines)