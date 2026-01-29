import pytest
from utils.validators import validate_name_only, is_valid_name

def test_validate_name_success():
    success, name, error = validate_name_only("  Иван Иванов  ")
    assert success is True
    assert name == "Иван Иванов"
    assert error == ""

def test_validate_name_too_short():
    success, name, error = validate_name_only("А")
    assert success is False
    assert "минимум 2 символа" in error

def test_validate_name_too_long():
    success, name, error = validate_name_only("A" * 51)
    assert success is False
    assert "слишком длинное" in error

@pytest.mark.parametrize("bad_name", [
    "12345",       # Нет букв
    "!!!",         # Только спецсимволы
    "   ",         # Пустота
    "Admin <script>" # Запрещенные символы
])
def test_validate_name_invalid_content(bad_name):
    success, _, _ = validate_name_only(bad_name)
    assert success is False

def test_is_valid_name_helper():
    assert is_valid_name("Алексей") is True
    assert is_valid_name("123") is False