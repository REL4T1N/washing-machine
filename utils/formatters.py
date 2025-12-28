from typing import List
from config.constants import DAYS_OF_WEEK

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

def format_washing_schedule_simple(data: List[List[str]]) -> str:
    """Упрощенное форматирование расписания"""
    if len(data) < 2:
        return "📭 Таблица пуста"
    
    lines = ["📅 <b>РАСПИСАНИЕ СТИРАЛЬНЫХ МАШИН</b>\n"]
        
    for day_idx, day_name in enumerate(DAYS_OF_WEEK):
        name_col_idx = day_idx * 2 + 1
        
        if day_idx * 2 >= len(data[0]):
            continue
        
        day_lines = [f"\n<b>{day_name}</b>", "─" * 20]
        
        for time_row_idx in range(1, min(9, len(data))):
            time_slot = data[time_row_idx][0] if data[time_row_idx] else ""
            
            booking = "свободно"
            if (len(data[time_row_idx]) > name_col_idx and 
                data[time_row_idx][name_col_idx] and 
                data[time_row_idx][name_col_idx].strip()):
                booking = data[time_row_idx][name_col_idx].strip()
            
            if time_slot:
                status = "🔴" if booking != "свободно" else "🟢"
                day_lines.append(f"{status} <b>{time_slot}</b>: {booking}")
        
        lines.extend(day_lines)
    
    return "\n".join(lines)