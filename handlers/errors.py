from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram import F

router = Router()

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