from aiogram.filters import BaseFilter
from aiogram.types import Message
from services.storage import UserStorage

class IsNamedUser(BaseFilter):
    """
    Фильтр проверяет, записано ли имя у пользователя в базе данных.
    """
    def __init__(self, storage: UserStorage):
        self.storage = storage

    async def __call__(self, message: Message) -> bool:
        # Теперь используем экземпляр, переданный при создании
        user = self.storage.get_user(message.from_user.id)
        # Пользователь должен существовать и поле name должно быть заполнено
        return user is not None and user.get("name") is not None