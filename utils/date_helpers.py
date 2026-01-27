from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

def create_booking_record(name: str, target_date: str) -> str:
    """
    Создает запись для таблицы в формате 'Имя дд.мм'
    Автоматически добавляет дату к имени

    Args:
        name: Имя пользователя.
        target_date: Дата в формате 'дд.мм'.

    Returns:
        str: Строка для записи в ячейку Google Таблицы.
    """
    cleaned_name = name.strip()
    cleaned_name = ' '.join(cleaned_name.split())
    return f"{cleaned_name} {target_date}"

def get_date_for_weekday(target_day_name: str, base_date: Optional[datetime] = None) -> datetime:
    """
    Вычисляет дату для заданного дня недели. Если день на этой неделе уже прошел,
    возвращает дату на следующую неделю.

    Args:
        target_day_name: Сокращенное название дня недели ("Пн", "Вт", и т.д.).
        base_date: Точка отсчета (по умолчанию сейчас).

    Returns:
        datetime: Объект даты, соответствующий выбранному дню.
    """
    # Маппинг дней на числовые
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
    
    # Если целевой день уже прошел на этой неделе - берем следующую
    if days_ahead < 0:
        days_ahead += 7
    
    return base_date + timedelta(days=days_ahead)

def parse_cell_content(cell_text: str) -> Optional[dict]:
    """
    Парсит содержимое ячейки 'Имя дд.мм'
    Возвращает словарь с именем и датой или None

    Args:
        cell_text: Содержимое ячейки Google Таблицы.

    Returns:
        Optional[dict]: Словарь с ключами 'name' и 'date', или None, если формат не совпал.
    """
    if not cell_text or not cell_text.strip():
        return None
    
    text = cell_text.strip()
    
    # Паттерн: имя (может содержать пробелы) + пробел + дата
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
    
    return None

def is_cell_available_for_date(cell_text: str, target_date_str: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет, доступна ли ячейка для указанной даты
    
    Логика:
    1. Пустая ячейка → доступна
    2. Запись с другой датой → доступна (можно перезаписать)
    3. Запись с такой же датой → занята
    4. Нечитаемая запись → занята (для безопасности)

    Args:
        cell_text: Текущее содержимое ячейки.
        target_date_str: Дата, на которую пользователь хочет записаться.

    Returns:
        Tuple[bool, Optional[str]]: (Доступно ли, Сообщение о причине отказа).
    """
    # 1. Пустая ячейка
    if not cell_text or not cell_text.strip():
        return True, None  # 1. Пустая ячейка
    
    # 2. Невозможно распарсить
    parsed = parse_cell_content(cell_text)
    if not parsed:
        return False, f"Невозможно прочитать запись: {cell_text}"
    
    # 3. Сравнение дат
    if parsed['date'] == target_date_str:
        return False, f"❌ Занято на {target_date_str}: {parsed['name']}"
    
    # 4. Даты разные - можно перезаписать
    return True, None

def get_date_for_day(selected_day: str) -> str:
    """
    Возвращает дату для выбранного дня недели в формате "дд.мм"

    Args:
        selected_day: Название дня недели ("Пн", "Вт"...).

    Returns:
        str: Дата в формате "дд.мм".
    """
    try:
        target_date = get_date_for_weekday(selected_day)
        return target_date.strftime("%d.%m")
    except Exception:
        return datetime.now().strftime("%d.%m")

def get_formatted_date_for_day(day_name: str) -> str:
    """Обертка над get_date_for_day для единообразия."""
    return get_date_for_day(day_name)

def is_date_expired(date_str: str) -> bool:
    """
    Проверяет, прошла ли дата (формат дд.мм).
    Считаем, что если дата "вчера" или раньше в этом году - она прошла. Учитываем смену года
    
    Args:
        date_str: Строка даты для проверки.

    Returns:
        bool: True, если дата уже прошла (считая до конца дня).
    """
    try:
        now = datetime.now()
        day, month = map(int, date_str.split('.'))
        
        # Объект даты текущего года
        booking_date = datetime(now.year, month, day, 23, 59)
        
        # Обработка перехода года
        if now.month == 1 and month == 12:
            booking_date = booking_date.replace(year=now.year - 1)
        elif now.month == 12 and month == 1:
            booking_date = booking_date.replace(year=now.year + 1)
            
        return booking_date < now
    except ValueError:
        return True # Если дата кривая, считаем "протухшей"
