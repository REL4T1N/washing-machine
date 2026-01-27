import logging

from aiogram import Router
from aiogram.types import Message, ErrorEvent
from aiogram import F

logger = logging.getLogger(__name__)

router = Router()

# Этот хендлер сработает на ЛЮБОЕ сообщение, если:
# 1. Это не /start (обработано в common)
# 2. Это не /name (обработано в user_commands)
# 3. Это не разрешенный /help (обработано в common)
# 4. У пользователя НЕТ имени (~IsNamedUser)
@router.message()
async def block_unnamed_actions(message: Message):
    await message.answer(
        "Извините, но мы не можем продолжить, пока вы не укажите имя.\n"
        "Воспользуйтесь командой /name. Например: /name Иван"
    )

@router.error(F.update.message.as_("message"))
async def error_handler(event: ErrorEvent):
    """Глобальный обработчик ошибок"""
    logger.exception("Произошла ошибка в хендлере", extra={"error": event.exception})

    if event.update.message:
        error_name = type(event.exception).__name__
        await event.update.message.answer(
            f"❌ Произошла непредвиденная ошибка: {error_name}\n"
            f"Попробуйте позже или обратитесь к администратору."
        )
    
    return True