from aiogram import Router
from aiogram.types import Message, ErrorEvent
from aiogram import F

from utils.filters import IsNamedUser

router = Router()

# Этот хендлер сработает на ЛЮБОЕ сообщение, если:
# 1. Это не /start (обработано в common)
# 2. Это не /name (обработано в user_commands)
# 3. Это не разрешенный /help (обработано в common)
# 4. У пользователя НЕТ имени (~IsNamedUser)
@router.message(~IsNamedUser())
async def block_unnamed_actions(message: Message):
    await message.answer(
        "Извините, но мы не можем продолжить, пока вы не укажите имя.\n"
        "Воспользуйтесь командой /name. Например: /name Иван"
    )

@router.error(F.update.message.as_("message"))
async def error_handler(event: ErrorEvent, message=None):
    """Глобальный обработчик ошибок"""
    error = event.exception
    
    if message:
        await message.answer(
            f"❌ Произошла ошибка: {str(error)[:100]}\n"
            f"Попробуйте позже или обратитесь к администратору."
        )
    
    # Логируем ошибку
    print(f"Error: {error}")
    return True