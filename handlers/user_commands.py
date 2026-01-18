from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

# Импортируем наше хранилище и валидатор
from services.storage import user_storage
from utils.validators import validate_name_only

router = Router()


# --- Хендлер команды /name ---
@router.message(Command("name"))
async def cmd_name(message: Message, command: CommandObject):
    user_id = message.from_user.id
    
    # Если пользователя нет в базе (странная ситуация, но обработаем как регистрацию)
    if not user_storage.user_exists(user_id):
        user_storage.add_user(user_id)

    # Получаем аргументы команды (то, что написано после /name)
    args = command.args
    
    if not args:
        await message.answer("Пожалуйста, укажите имя после команды. Например: /name Иван")
        return

    raw_name = args.strip()

    # 1. Валидация формата 
    is_valid, cleaned_name, error_msg = validate_name_only(raw_name)

    if not is_valid:
        await message.answer(f"Ошибка валидации: {error_msg}")
        return

    # 2. Проверка на уникальность (среди других пользователей)
    # Важно: если пользователь вводит СВОЕ же имя повторно, это не должно быть ошибкой,
    # но в простой реализации is_name_taken скажет True. 
    # Сделаем проверку: если имя занято И это не текущий пользователь.
    
    current_user_data = user_storage.get_user(user_id)
    current_name = current_user_data.get("name")
    
    # Если имя занято кем-то другим
    if user_storage.is_name_taken(cleaned_name):
        # Если это имя уже принадлежит текущему пользователю, просто скажем ОК (или можно игнорировать)
        if current_name and current_name.lower() == cleaned_name.lower():
             await message.answer("Это имя уже установлено у вас.")
             return
             
        await message.answer(
            "Данное имя уже используется другим пользователем. "
            "Укажите новое имя командой /name, например: /name Иван"
        )
        return

    # 3. Успешное сохранение
    user_storage.set_user_name(user_id, cleaned_name)
    
    await message.answer(
        f"Приятно познакомиться, {cleaned_name}.\n\n"
        "Доступные команды:\n"
        "/table - таблица с записями к текущему моменту\n"
        "/help - подробная справка\n"
        "/name - установить новое имя\n"
        "/bookings - управление активными записями"
    )
