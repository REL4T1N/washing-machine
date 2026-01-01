from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

def create_booking_record(name: str, target_date: str) -> str:
    """
    Создает запись для таблицы в формате 'Имя дд.мм'
    Автоматически добавляет дату к имени
    """
    cleaned_name = name.strip()
    # Убираем лишние пробелы в имени
    cleaned_name = ' '.join(cleaned_name.split())
    return f"{cleaned_name} {target_date}"

def get_date_for_weekday(target_day_name: str, base_date: datetime = None) -> datetime:
    """
    Получает дату для дня недели по его названию
    
    target_day_name: "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"
    base_date: дата, от которой отсчитываем (по умолчанию сегодня)
    """
    # Маппинг русских названий дней на числовые
    day_mapping = {
        "Пн": 0, "Вт": 1, "Ср": 2, "Чт": 3,
        "Пт": 4, "Сб": 5, "Вс": 6
    }
    
    if target_day_name not in day_mapping:
        raise ValueError(f"Неизвестный день недели: {target_day_name}")
    
    if base_date is None:
        base_date = datetime.now()
    
    target_weekday = day_mapping[target_day_name]
    current_weekday = base_date.weekday()
    
    # Разница дней до целевого дня недели
    days_ahead = target_weekday - current_weekday
    
    # Если целевой день уже прошел на этой неделе, берем следующую неделю
    if days_ahead < 0:
        days_ahead += 7
    
    return base_date + timedelta(days=days_ahead)

def parse_cell_content(cell_text: str) -> Optional[dict]:
    """
    Парсит содержимое ячейки 'Имя дд.мм'
    Возвращает словарь с именем и датой или None
    """
    if not cell_text or not cell_text.strip():
        return None
    
    # Убираем лишние пробелы
    text = cell_text.strip()
    
    # Паттерн: имя (может содержать пробелы) + пробел + дата
    # Ищем дату в конце строки
    pattern = r'^(.+?)\s+(\d{1,2}\.\d{1,2})$'
    match = re.match(pattern, text)
    
    if match:
        name = match.group(1).strip()
        date_str = match.group(2).strip()
        return {
            'name': name,
            'date': date_str,
            'full_text': text
        }
    
    # Если нет даты в формате дд.мм, проверяем другие форматы
    pattern2 = r'^(.+?)\s+(\d{1,2}[.,]\d{1,2})$'
    match2 = re.match(pattern2, text)
    if match2:
        # Пытаемся нормализовать дату (заменяем запятые на точки)
        name = match2.group(1).strip()
        date_str = match2.group(2).strip().replace(',', '.')
        return {
            'name': name,
            'date': date_str,
            'full_text': text
        }
    
    return None

def is_cell_available_for_date(cell_text: str, target_date_str: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет, доступна ли ячейка для указанной даты
    
    Логика:
    1. Пустая ячейка → доступна
    2. Запись с другой датой → доступна (можно перезаписать)
    3. Запись с такой же датой → занята
    4. Нечитаемая запись → занята (для безопасности)
    """
    if not cell_text or not cell_text.strip():
        return True, None  # 1. Пустая ячейка
    
    parsed = parse_cell_content(cell_text)
    if not parsed:
        # Не можем распарсить - считаем занятой
        return False, f"Невозможно прочитать запись: {cell_text}"
    
    if not parsed.get('date'):
        # Есть имя, но нет даты (старый формат?) 
        # Можно перезаписать
        return True, None
    
    # Сравниваем даты
    if parsed['date'] == target_date_str:
        return False, f"❌ Занято на {target_date_str}: {parsed['name']}"
    
    # Даты разные - можно перезаписать
    return True, None

def get_date_for_day(selected_day: str) -> str:
    """
    Получает дату для выбранного дня недели в формате "дд.мм"
    """
    try:
        target_date = get_date_for_weekday(selected_day)
        return target_date.strftime("%d.%m")
    except Exception as e:
        # В случае ошибки возвращаем сегодняшнюю дату
        return datetime.now().strftime("%d.%m")
    
def get_formatted_date_for_day(day_name: str) -> str:
    """
    Удобная обертка: получает дату для дня недели в формате 'дд.мм'
    Используется в интерфейсе для показа пользователю
    """
    date_obj = get_date_for_weekday(day_name)
    return date_obj.strftime("%d.%m")