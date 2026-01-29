import pytest
from utils.helpers import get_cell_address, cell_to_indices, get_human_readable_slot

def test_get_cell_address_valid():
    # Пн -> B, 8:00-9:00 -> 2. Итог: B2, 2
    address, row = get_cell_address("Пн", "8:00-9:00")
    assert address == "B2"
    assert row == 2

def test_get_cell_address_invalid():
    address, row = get_cell_address("НесуществующийДень", "8:00-9:00")
    assert address is None
    assert row is None

def test_cell_to_indices():
    # B2 -> Индексы (row=1, col=1) так как в Python 0-based
    assert cell_to_indices("B2") == (1, 1)
    # N9 -> Последняя ячейка из конфига
    assert cell_to_indices("N9") == (8, 13)

def test_get_human_readable_slot():
    assert get_human_readable_slot("B2") == "Пн 8:00-9:00"
    assert get_human_readable_slot("N9") == "Вс 22:00-23:00"
    assert get_human_readable_slot("Z100") == "??? ??:??" # Неизвестные координаты