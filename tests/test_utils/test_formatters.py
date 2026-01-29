import pytest
from unittest.mock import patch
from utils.formatters import split_message, format_washing_schedule_simple

def test_split_message():
    text = "Line1\nLine2\nLine3"
    # Разбиваем по 10 символов
    parts = split_message(text, max_length=10)
    assert len(parts) > 1
    assert parts[0] == "Line1"

@patch('utils.formatters.get_date_for_day')
def test_format_washing_schedule_simple(mock_get_date):
    # Допустим, сегодня для Пн дата "20.05"
    mock_get_date.side_effect = lambda day: "20.05" if day == "Пн" else "21.05"
    
    # Имитируем данные из Google Sheets (Заголовок + 1 строка времени)
    data = [
        ["Время", "Пн", "", "Вт", ""], # Шапка
        ["8:00-9:00", "Иван 20.05", "", "Петр 19.05", ""] # Петр записан на прошлую неделю
    ]
    
    result = format_washing_schedule_simple(data, "http://link")
    
    assert "Иван 20.05" in result # Актуальная запись
    assert "Петр 19.05" not in result # Старая запись должна скрыться
    assert "🟢 <b>8:00-9:00</b>: свободно" in result # Вместо Петра должно быть свободно