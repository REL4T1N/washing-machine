import pytest
from unittest.mock import AsyncMock, MagicMock
from utils.filters import IsNamedUser

@pytest.mark.asyncio
async def test_is_named_user_filter_allowed():
    # Создаем фейковое хранилище
    mock_storage = MagicMock()
    # Настраиваем, что для ID 123 вернется пользователь с именем
    mock_storage.get_user.return_value = {"name": "Алексей"}
    
    filter_obj = IsNamedUser(storage=mock_storage)
    
    # Создаем фейковое сообщение от Telegram
    mock_message = AsyncMock()
    mock_message.from_user.id = 123
    
    result = await filter_obj(mock_message)
    assert result is True

@pytest.mark.asyncio
async def test_is_named_user_filter_denied():
    mock_storage = MagicMock()
    # Пользователь без имени или не существует
    mock_storage.get_user.return_value = {"name": None}
    
    filter_obj = IsNamedUser(storage=mock_storage)
    
    mock_message = AsyncMock()
    mock_message.from_user.id = 999
    
    result = await filter_obj(mock_message)
    assert result is False