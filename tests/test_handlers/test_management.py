import pytest
from handlers.booking.management import confirm_delete_handler

@pytest.mark.asyncio
async def test_delete_booking_success(mock_callback, mock_booking_service, mock_storage):
    # Настройка
    mock_callback.data = "confirm_delete_B2"
    mock_booking_service.delete_booking.return_value = (True, "")
    
    await confirm_delete_handler(mock_callback, mock_storage, mock_booking_service)
    
    mock_booking_service.delete_booking.assert_called_once_with("B2", 123)
    mock_callback.answer.assert_called_with("✅ Запись удалена")

@pytest.mark.asyncio
async def test_delete_booking_error(mock_callback, mock_booking_service, mock_storage):
    # Настройка ошибки
    mock_callback.data = "confirm_delete_B2"
    mock_booking_service.delete_booking.return_value = (False, "Ошибка API")
    
    await confirm_delete_handler(mock_callback, mock_storage, mock_booking_service)
    
    # Сообщение об ошибке
    mock_callback.message.edit_text.assert_called()