from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from services.storage import user_storage
from services.google_sheets import google_sheets_service
from services.booking_service import get_cached_table, invalidate_table_cache
from utils.validators import validate_name_only
from utils.date_helpers import create_booking_record
from config.config import SHEET_NAME

router = Router()

@router.message(Command("name"))
async def cmd_name(message: Message, command: CommandObject):
    user_id = message.from_user.id
    
    if not user_storage.user_exists(user_id):
        user_storage.add_user(user_id)

    args = command.args
    if not args:
        await message.answer("Пожалуйста, укажите имя после команды. Например: /name Иван")
        return

    raw_name = args.strip()

    # 1. Валидация
    is_valid, cleaned_name, error_msg = validate_name_only(raw_name)
    if not is_valid:
        await message.answer(f"Ошибка валидации: {error_msg}")
        return

    # 2. Проверка уникальности
    current_user_data = user_storage.get_user(user_id)
    current_name = current_user_data.get("name")
    
    if user_storage.is_name_taken(cleaned_name):
        if current_name and current_name.lower() == cleaned_name.lower():
             await message.answer("Это имя уже установлено у вас.")
             return
        await message.answer(
            "Данное имя уже используется другим пользователем. "
            "Укажите новое имя командой /name, например: /name Иван"
        )
        return

    # 3. Логика обновления записей
    # Если у пользователя уже есть имя, значит, у него могут быть записи со старым именем
    if current_name:
        wait_msg = await message.answer("🔄 Обновляю ваше имя и записи...")
        
        # Получаем актуальные записи пользователя
        # Сначала синхронизируем с таблицей, чтобы не обновлять "мертвые" ячейки
        try:
            table_data = await get_cached_table(force_refresh=True)
            user_bookings = user_storage.sync_user_bookings(user_id, table_data)
            
            if user_bookings:
                # Формируем пакет обновлений для Google Sheets
                updates = []
                for cell, date_str in user_bookings.items():
                    # Создаем новую строку "НовоеИмя Дата"
                    new_value = create_booking_record(cleaned_name, date_str)
                    updates.append({
                        'range': cell,
                        'values': [[new_value]]
                    })
                
                # Отправляем одним запросом (batchUpdate)
                try:
                    await google_sheets_service.batch_update_values(SHEET_NAME, updates)
                    invalidate_table_cache() # Сбрасываем кэш, так как таблица изменилась
                except Exception as e:
                    await wait_msg.edit_text(f"⚠️ Имя сохранено, но не удалось обновить записи в таблице: {e}")
                    # Все равно сохраняем имя в базе, чтобы не было рассинхрона
                    user_storage.set_user_name(user_id, cleaned_name)
                    return

                await wait_msg.edit_text(
                    f"Приятно познакомиться, {cleaned_name}. {len(updates)} записей обновлены.\n\n"
                    "Доступные команды:\n"
                    "/table - таблица с записями к текущему моменту\n"
                    "/help - подробная справка\n"
                    "/name - установить новое имя\n"
                    "/bookings - управление активными записями"
                    )
            else:
                 await wait_msg.delete()

        except Exception as e:
            # Если что-то упало при работе с сетью, просто логируем, но имя меняем
            print(f"Ошибка при обновлении записей смены имени: {e}")
            if wait_msg: 
                await wait_msg.delete()

    else:
        await message.answer(
            f"Приятно познакомиться, {cleaned_name}.\n\n"
            "Доступные команды:\n"
            "/table - таблица с записями к текущему моменту\n"
            "/help - подробная справка\n"
            "/name - установить новое имя\n"
            "/bookings - управление активными записями"
        )

    # 4. Сохранение нового имени в базу
    user_storage.set_user_name(user_id, cleaned_name)