import pytest
from handlers.common import cmd_start
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_cmd_start_with_name(mock_message, mock_storage):
    # Настраиваем хранилище
    mock_storage.get_user.return_value = {"name": "Александр"}
    
    # Запускаем хендлер
    await cmd_start(mock_message, mock_storage, MagicMock())

    # Проверяем ответ
    mock_message.answer.assert_called_once()
    assert "Здравствуйте, Александр" in mock_message.answer.call_args[0][0]