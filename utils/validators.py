import re
from typing import Tuple

def validate_name_date_input(text: str) -> Tuple[bool, str, str, str]:
    """
    Проверяет ввод имени и даты
    Возвращает (корректно ли, имя, дата, сообщение об ошибке)
    """
    text = text.strip()
    
    if len(text) < 3:
        return False, "", "", "Слишком короткий ввод. Нужно: Имя дд.мм"
    
    parts = text.split()
    
    if len(parts) < 2:
        return False, "", "", "Нужно ввести имя и дату через пробел"
    
    name = " ".join(parts[:-1])
    date_str = parts[-1]
    
    if len(name) < 2:
        return False, "", "", "Имя должно быть минимум 2 символа"
    
    # Проверяем дату
    date_pattern = r'^\d{1,2}\.\d{1,2}$'
    if not re.match(date_pattern, date_str):
        return False, "", "", "Неверный формат даты. Используйте: дд.мм (например: 25.12)"
    
    try:
        day, month = map(int, date_str.split('.'))
        
        if month < 1 or month > 12:
            return False, "", "", "Месяц должен быть от 1 до 12"
        
        if day < 1 or day > 31:
            return False, "", "", "День должен быть от 1 до 31"
        
        if month == 2 and day > 29:
            return False, "", "", "В феврале максимум 29 дней"
        
        if month in [4, 6, 9, 11] and day > 30:
            return False, "", "", f"В {month} месяце максимум 30 дней"
            
    except ValueError:
        return False, "", "", "Ошибка в формате даты"
    
    formatted_date = f"{day:02d}.{month:02d}"
    
    return True, name, formatted_date, ""