import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import User, Chat, Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

# --- Объекты Telegram ---
@pytest.fixture
def mock_user():
    # Реальный объект User, а не Mock!
    return User(id=123, is_bot=False, first_name="TestUser", username="testuser")

@pytest.fixture
def mock_chat():
    return Chat(id=123, type="private")

@pytest.fixture
def mock_message(mock_user, mock_chat):
    message = AsyncMock(spec=Message)
    # Привязываем реального юзера и чат
    message.from_user = mock_user
    message.chat = mock_chat
    # Важно: answer должен быть асинхронным
    message.answer = AsyncMock()
    # Метод edit_text тоже
    message.edit_text = AsyncMock()
    return message

@pytest.fixture
def mock_callback(mock_user, mock_message):
    callback = AsyncMock(spec=CallbackQuery)
    callback.from_user = mock_user
    callback.message = mock_message
    callback.answer = AsyncMock()
    callback.data = "some_data"
    return callback

# --- Сервисы и FSM ---
@pytest.fixture
def mock_storage():
    storage = AsyncMock()

    # === СИНХРОННЫЕ МЕТОДЫ (MagicMock) ===
    # Они должны возвращать значение сразу, без await
    storage.user_exists = MagicMock(return_value=True)
    storage.get_user = MagicMock(return_value={"name": "Александр"})
    storage.is_name_taken = MagicMock(return_value=False) 
    storage.get_owner_by_cell = MagicMock(return_value=None)
    
    # === АСИНХРОННЫЕ МЕТОДЫ (AsyncMock) ===
    # Они уже являются AsyncMock по умолчанию из-за storage = AsyncMock(),
    # но можно настроить их явно для ясности
    storage.set_user_name = AsyncMock()
    storage.sync_user_bookings = AsyncMock(return_value={})
    
    return storage

@pytest.fixture
def mock_booking_service():
    return AsyncMock()

@pytest.fixture
def mock_gs_service():
    return AsyncMock()

@pytest.fixture
async def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=123, chat_id=123, user_id=123)
    return FSMContext(storage=storage, key=key)