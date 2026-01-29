import pytest
from services.storage import UserStorage

@pytest.fixture
async def storage(tmp_path): # Переименовал для удобства
    """Фикстура для создания временного хранилища"""
    test_file = tmp_path / "test_users.json"
    storage_obj = UserStorage(filename=str(test_file))
    # Инициализируем базовую структуру, если нужно (add_user это делает)
    return storage_obj

@pytest.mark.asyncio
async def test_add_and_get_user(storage):
    await storage.add_user(123)
    await storage.set_user_name(123, "Алексей")
    
    user = storage.get_user(123)
    assert user["name"] == "Алексей"
    assert storage.user_exists(123) is True

@pytest.mark.asyncio
async def test_persistence(tmp_path):
    test_file = tmp_path / "persistence.json"
    
    storage1 = UserStorage(filename=str(test_file))
    await storage1.add_user(456)
    await storage1.set_user_name(456, "Тест")
    
    storage2 = UserStorage(filename=str(test_file))
    await storage2.load()
    
    assert storage2.user_exists(456) is True
    assert storage2.get_user(456)["name"] == "Тест"

@pytest.mark.asyncio
async def test_sync_user_bookings_removes_ghosts(storage):
    user_id = 777
    await storage.add_user(user_id)
    await storage.set_user_name(user_id, "Иван")
    await storage.add_booking(user_id, "B2", "20.05")
    
    fake_table_data = [
        ["Время", "Пн"],
        ["8:00-9:00", ""] # Пусто
    ]
    
    updated_bookings = await storage.sync_user_bookings(user_id, fake_table_data)
    assert "B2" not in updated_bookings

@pytest.mark.asyncio
async def test_sync_removes_mismatched_name(storage): # Теперь имя фикстуры совпадает
    user_id = 1
    await storage.add_user(user_id)
    await storage.set_user_name(user_id, "Тест")
    await storage.add_booking(user_id, "B2", "20.05")
    
    table_data = [
        ["Время", "Пн"],
        ["8:00-9:00", "Мария 20.05"] 
    ]
    
    await storage.sync_user_bookings(user_id, table_data)
    assert storage.get_user_bookings(user_id) == {}