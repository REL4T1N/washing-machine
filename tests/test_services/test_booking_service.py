import pytest
from unittest.mock import AsyncMock, MagicMock
from services.booking_service import BookingService
# from datetime import datetime

@pytest.fixture
def mock_gs():
    return AsyncMock()

@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    # По умолчанию пользователь существует и имеет имя
    storage.get_user = MagicMock(return_value={"name": "Алексей"})
    return storage

@pytest.fixture
def booking_service(mock_gs, mock_storage):
    return BookingService(
        gs_service=mock_gs,
        user_storage=mock_storage,
        sheet_name="Sheet1",
        cache_ttl=60
    )

@pytest.mark.asyncio
async def test_get_table_data_uses_cache(booking_service, mock_gs):
    # Настраиваем возврат данных
    mock_gs.get_data.return_value = [["data"]]
    
    # Первый вызов - идет в GS
    await booking_service.get_table_data()
    # Второй вызов - должен взять из кэша
    await booking_service.get_table_data()
    
    # Проверяем, что вызов к API был всего ОДИН раз
    assert mock_gs.get_data.call_count == 1

@pytest.mark.asyncio
async def test_book_slot_occupied_error(booking_service, mock_gs):
    # Имитируем, что ячейка уже занята кем-то другим на ту же дату
    mock_gs.get_data.return_value = [["Иван 20.05"]]
    
    success, message = await booking_service.book_slot(
        user_id=123, day="Пн", time_slot="8:00-9:00", target_date="20.05"
    )
    
    assert success is False
    assert "Занято" in message
    # Проверяем, что запись не была вызвана
    mock_gs.write_value.assert_not_called()

@pytest.mark.asyncio
async def test_book_slot_success(booking_service, mock_gs, mock_storage):
    # Имитируем пустую ячейку
    mock_gs.get_data.return_value = [[""]]
    mock_gs.write_value.return_value = True
    
    success, message = await booking_service.book_slot(
        user_id=123, day="Пн", time_slot="8:00-9:00", target_date="20.05"
    )
    
    assert success is True
    mock_storage.add_booking.assert_called_once()
