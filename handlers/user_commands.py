from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from config.settings import google_settings

from services.storage import UserStorage
from services.google_sheets import GoogleSheetsService
from services.booking_service import BookingService

from utils.validators import validate_name_only

router = Router()

@router.message(Command("name"))
async def cmd_name(
    message: Message, 
    command: CommandObject,
    storage: UserStorage,
    booking_service: BookingService,
    gs_service: GoogleSheetsService,
):
    """Установка или смена имени. Обновляет все записи в таблице при смене."""
    user_id = message.from_user.id
    
    if not storage.user_exists(user_id):
        await storage.add_user(user_id)

    args = command.args
    if not args:
        await message.answer(
            "Пожалуйста, укажите имя после команды. Например: /name Иван"
        )
        return

    raw_name = args.strip()

    # 1. Валидация
    is_valid, cleaned_name, error_msg = validate_name_only(raw_name)
    if not is_valid:
        await message.answer(f"Ошибка валидации: {error_msg}")
        return

    # 2. Проверка уникальности
    current_user_data = storage.get_user(user_id)
    current_name = current_user_data.get("name")
    
    if storage.is_name_taken(cleaned_name):
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
            table_data = await booking_service.get_table_data(force_refresh=True)
            user_bookings = await storage.sync_user_bookings(user_id, table_data)


            if user_bookings:
                # Формируем пакет обновлений для Google Sheets
                updates = []
                for cell, date_str in user_bookings.items():
                    # Создаем новую строку "НовоеИмя Дата"
                    new_value = f"{cleaned_name} {date_str}"
                    updates.append({
                        'range': cell,
                        'values': [[new_value]]
                    })
                
                # Отправляем одним запросом (batchUpdate)
                success = await gs_service.batch_update_values(google_settings.sheet_name, updates)
                if success:
                    await storage.set_user_name(user_id, cleaned_name)
                    await booking_service.invalidate_cache()
                    await wait_msg.edit_text(
                        f"✅ Имя обновлено на '{cleaned_name}'. "
                        f"{len(updates)} записей в таблице изменены."
                    )

                else:
                    await wait_msg.edit_text(
                        "⚠️ Ошибка связи с Google Sheets. Имя НЕ изменено. "
                        "Попробуйте еще раз через минуту."
                    )

            else:
                await storage.set_user_name(user_id, cleaned_name)
                await wait_msg.edit_text(f"✅ Имя изменено на <b>{cleaned_name}</b>.")

        except Exception as e:
            await wait_msg.edit_text(f"⚠️ Произошла ошибка: {e}. Имя не изменено.")
    
    else:
        await storage.set_user_name(user_id, cleaned_name)
        await message.answer(
            f"Приятно познакомиться, {cleaned_name}.\n\n"
            "Теперь вы можете пользоваться ботом. Начните с команды /table."
        )
