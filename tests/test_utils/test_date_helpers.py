import pytest
from datetime import datetime
from unittest.mock import patch
from utils.date_helpers import (
    get_date_for_weekday, 
    parse_cell_content, 
    is_date_expired,
    is_cell_available_for_date
)

# Фиксируем дату как Понедельник 20 мая 2024 года
FIXED_NOW = datetime(2024, 5, 20, 12, 0) 

@patch('utils.date_helpers.datetime')
def test_get_date_for_weekday_same_week(mock_datetime):
    mock_datetime.now.return_value = FIXED_NOW
    
    # Пятница этой же недели (24 мая)
    result = get_date_for_weekday("Пт")
    assert result.day == 24
    assert result.month == 5

@patch('utils.date_helpers.datetime')
def test_get_date_for_weekday_next_week(mock_datetime):
    mock_datetime.now.return_value = FIXED_NOW
    
    # Вс прошло (хотя Пн только начался, но если бы мы просили Вс, который был вчера)
    # По логике функции, если мы в Пн просим Пн - это сегодня.
    # Если просим Вс (который 19-го прошел) - это будет 26-е.
    result = get_date_for_weekday("Вс")
    # Т.к. 20 мая - Пн (0), а Вс - (6). 6-0 = 6. 20+6 = 26.
    assert result.day == 26

def test_parse_cell_content():
    assert parse_cell_content("Иван 20.05") == {'name': 'Иван', 'date': '20.05', 'full_text': 'Иван 20.05'}
    assert parse_cell_content("Имя Фамилия 01.12") == {'name': 'Имя Фамилия', 'date': '01.12', 'full_text': 'Имя Фамилия 01.12'}
    assert parse_cell_content("Просто текст") is None
    assert parse_cell_content("") is None

@patch('utils.date_helpers.datetime')
def test_is_date_expired(mock_datetime):
    mock_datetime.now.return_value = FIXED_NOW # 20.05.2024
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
    
    assert is_date_expired("19.05") is True  # Вчера
    assert is_date_expired("21.05") is False # Завтра

def test_is_cell_available_for_date():
    # Свободно, если пусто
    available, error = is_cell_available_for_date("", "20.05")
    assert available is True
    
    # Свободно, если дата другая
    available, error = is_cell_available_for_date("Иван 19.05", "20.05")
    assert available is True
    
    # Занято, если дата та же
    available, error = is_cell_available_for_date("Иван 20.05", "20.05")
    assert available is False
    assert "Занято" in error