from aiogram.filters import BaseFilter
from aiogram.types import Message
from services.storage import user_storage

class IsNamedUser(BaseFilter):
    """
    Фильтр проверяет, записано ли имя у пользователя в базе данных.
    """
    async def __call__(self, message: Message) -> bool:
        user = user_storage.get_user(message.from_user.id)
        # Пользователь должен существовать и поле name должно быть заполнено
        return user is not None and user.get("name") is not None