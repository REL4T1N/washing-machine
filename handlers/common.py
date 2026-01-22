from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

# Импортируем наше хранилище и валидатор
from services.storage import UserStorage

# from utils.filters import IsNamedUser

router = Router()

# --- Хендлер команды /start ---
@router.message(CommandStart())
async def cmd_start(message: Message, storage: UserStorage):
    user_id = message.from_user.id
    user = storage.get_user(user_id)

    # 1. Если пользователя вообще нет в базе
    if not user:
        await storage.add_user(user_id)
        await message.answer(
            "Добро пожаловать. Данный бот предназначен для записи в таблицу[ссылка].\n"
            "Чтобы записаться укажите имя, которое будет использоваться в дальнейшем командой /name. "
            "Например: /name Иван"
        )
        return

    # 2. Если пользователь есть, проверяем поле name
    name = user.get("name")
    
    if name:
        # Пользователь есть и имя задано
        await message.answer(
            f"Здравствуйте, {name}\n\n"
            "Доступные команды:\n"
            "/table - таблица с записями к текущему моменту\n"
            "/help - подробная справка\n"
            "/name - установить новое имя\n"
            "/bookings - управление активными записями"
        )
    else:
        # Пользователь есть, но имени нет (повторный /start без регистрации)
        await message.answer(
            "Добро пожаловать. Данный бот предназначен для записи в таблицу[ссылка]. \n"
            "Чтобы записаться укажите имя, которое будет использоваться в дальнейшем командой /name. "
            "Например: /name Иван"
        )

# --- Команда /help ---
# Мы используем IsNamedUser(). Если у пользователя НЕТ имени, этот хендлер проигнорируется,
# и бот пойдет искать дальше (и попадет в блокирующий хендлер в errors.py).
@router.message(Command("help"))#, IsNamedUser())
async def cmd_help(message: Message):
    text = (
        "Инструкция по использованию:\n\n"
        "1. Настройка информации и пользователе\n"
        "…\n\n"
        "2. Как записаться на стирку?\n"
        "…\n\n"
        "3. Управление моими записями?\n"
        "…\n\n"
        "4. Что делать, если кто-то перезаписал меня?\n"
        "…\n\n"
        "5. Информация о разработке, форма для обратной связи\n"
        "…"
    )
    await message.answer(text)