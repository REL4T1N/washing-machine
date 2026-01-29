import pytest
from aiogram.filters import CommandObject
from handlers.user_commands import cmd_name
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_cmd_name_success_first_time(mock_message, mock_storage, mock_booking_service, mock_gs_service):
    # Настройка
    mock_storage.get_user.return_value = {"name": None}
    mock_storage.is_name_taken.return_value = False
    
    # Команда /name Иван
    command = CommandObject(prefix="/", command="name", args="Иван")

    await cmd_name(mock_message, command, mock_storage, mock_booking_service, mock_gs_service)

    # Проверки
    mock_storage.set_user_name.assert_called_once_with(123, "Иван")
    mock_message.answer.assert_called()

@pytest.mark.asyncio
async def test_cmd_name_change_with_sync(mock_message, mock_storage, mock_booking_service, mock_gs_service):
    # Настройка
    mock_storage.get_user.return_value = {"name": "СтароеИмя"}
    mock_storage.is_name_taken.return_value = False
    
    # Имитируем, что нужно обновить запись в таблице
    mock_storage.sync_user_bookings.return_value = {"B2": "20.05"}
    mock_gs_service.batch_update_values.return_value = True

    # Трюк: message.answer возвращает сообщение, которое потом редактируют
    wait_msg = AsyncMock()
    mock_message.answer.return_value = wait_msg
    
    command = CommandObject(prefix="/", command="name", args="НовоеИмя")

    await cmd_name(mock_message, command, mock_storage, mock_booking_service, mock_gs_service)

    # Проверка вызова Google Sheets
    mock_gs_service.batch_update_values.assert_called_once()
    # Проверка, что сообщение отредактировалось
    wait_msg.edit_text.assert_called()