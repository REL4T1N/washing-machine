import asyncio
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from services.google_sheets import google_sheets_service
from services.lock_service import LockService
from keyboards.inline import get_main_menu_keyboard
from utils.formatters import format_washing_schedule_simple, split_message
from utils.validators import validate_name_date_input
from utils.helpers import get_cell_address
# from config.config import config
from config.config import SHEET_NAME
from config.constants import DAYS_OF_WEEK, TIME_SLOTS
from states.booking_states import BookingState

router = Router()

@router.message(Command("table"))
async def get_table(message: Message, state: FSMContext):
    """Обработчик команды /table - отображение таблицы"""
    await show_table(message, state)

async def show_table(message: Message, state: FSMContext, is_update: bool = False, callback=None):
    """Показывает таблицу (используется и для команды, и для обновления)"""
    try:
        range_input = "A1:N9"
        result = await google_sheets_service.get_data(SHEET_NAME, range_input)
        
        if not result or not result[0]:
            text = "📭 Таблица пуста"
        else:
            text = format_washing_schedule_simple(result)
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            messages = split_message(text, 4000)
            for i, msg in enumerate(messages):
                if i == len(messages) - 1:
                    if is_update and callback:
                        await callback.message.edit_text(
                            text=msg, 
                            parse_mode="HTML", 
                            reply_markup=get_main_menu_keyboard()
                        )
                        await callback.answer("✅ Данные обновлены", show_alert=False)
                    else:
                        await message.answer(
                            text=msg, 
                            parse_mode="HTML", 
                            reply_markup=get_main_menu_keyboard()
                        )
                else:
                    await message.answer(text=msg, parse_mode="HTML")
            await state.clear()
            return

        if is_update and callback:
            try:
                await callback.message.edit_text(
                    text=text,
                    parse_mode="HTML",
                    reply_markup=get_main_menu_keyboard()
                )
                await callback.answer("✅ Данные обновлены", show_alert=False)
            except Exception as e:
                if "message is not modified" in str(e):
                    await callback.answer("✅ Данные уже актуальны", show_alert=False)
                else:
                    await callback.message.answer(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=get_main_menu_keyboard()
                    )
                    await callback.answer("✅ Данные обновлены (отправлено новое сообщение)", show_alert=False)
        else:
            await message.answer(
                text=text,
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        
        await state.clear()
    
    except Exception as e:
        error_text = f"❌ Ошибка при чтении: {str(e)[:100]}"
        if is_update and callback:
            await callback.message.edit_text(
                text=error_text,
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer("❌ Ошибка при обновлении", show_alert=True)
        else:
            await message.answer(
                text=error_text,
                reply_markup=get_main_menu_keyboard()
            )
        await state.clear()

@router.message(BookingState.entering_name)
async def enter_name_handler(message: Message, state: FSMContext):
    """Обработчик ввода имени и даты"""
    user_input = message.text.strip()
    
    is_valid, name, date, error_msg = validate_name_date_input(user_input)
    
    if not is_valid:
        await message.answer(
            text=f"❌ {error_msg}\n\n"
                 f"Попробуйте еще раз в формате: <code>Имя дд.мм</code>\n"
                 f"<i>Например: Иван 25.12</i>",
            parse_mode="HTML"
        )
        return
    
    data = await state.get_data()
    day = data.get('selected_day')
    time_slot = data.get('selected_time')
    
    if not day or not time_slot:
        await message.answer("❌ Ошибка: данные о времени утеряны. Начните заново.")
        await state.clear()
        return
    
    value_to_write = f"{name} {date}"
    
    processing_msg = await message.answer("⏳ Проверяю доступность времени...")
    
    try:
        success, error_msg = await write_to_sheet_with_lock(day, time_slot, value_to_write)
        
        if success:
            await processing_msg.delete()
            
            await message.answer(
                text=f"✅ <b>Запись успешно добавлена!</b>\n\n"
                     f"📅 День: <b>{day}</b>\n"
                     f"⏰ Время: <b>{time_slot}</b>\n"
                     f"👤 Запись: <b>{value_to_write}</b>\n\n"
                     f"Нажмите 'Обновить', чтобы увидеть изменения в таблице.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await processing_msg.edit_text(
                text=f"❌ <b>Не удалось записаться:</b>\n{error_msg}\n\n"
                     f"Пожалуйста, выберите другое время или попробуйте позже.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
            
    except Exception as e:
        await processing_msg.edit_text(
            text=f"❌ <b>Критическая ошибка:</b>\n{str(e)}\n\n"
                 f"Пожалуйста, обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()

async def write_to_sheet_with_lock(day: str, time_slot: str, value: str) -> tuple[bool, str]:
    """
    Записывает значение в таблицу с блокировкой и проверкой
    Возвращает (успешно ли, сообщение об ошибке)
    """
    try:
        # Определяем адрес ячейки
        cell_address, row = get_cell_address(day, time_slot)
        
        if not cell_address:
            return False, "Неизвестный день или время"
        
        # Пытаемся получить блокировку
        lock_acquired = LockService.acquire_lock(cell_address)
        if not lock_acquired:
            return False, "❌ Слишком много попыток записи. Попробуйте через 10 секунд."
        
        try:
            # Проверяем, свободна ли ячейка
            is_free, current_value, error_msg = await is_cell_free(cell_address)
            
            if not is_free:
                if error_msg:
                    return False, error_msg
                else:
                    return False, f"❌ Ячейка уже занята: <b>{current_value}</b>"
            
            # Записываем значение
            success = await google_sheets_service.write_value(
                sheet_name=SHEET_NAME,
                cell=cell_address,
                value=value
            )
            
            if not success:
                return False, "Ошибка записи в таблицу"
            
            # Краткая проверка
            await asyncio.sleep(0.3)
            verify_result = await google_sheets_service.get_data(SHEET_NAME, cell_address)
            
            if verify_result and verify_result[0]:
                written_value = verify_result[0][0] if verify_result[0] else ""
                if written_value.strip() != value.strip():
                    # Откатываем
                    try:
                        await google_sheets_service.write_value(
                            sheet_name=SHEET_NAME,
                            cell=cell_address,
                            value=""
                        )
                    except:
                        pass
                    return False, "❌ Ошибка верификации записи. Попробуйте еще раз."
            
            return True, ""
            
        finally:
            # Всегда освобождаем блокировку
            LockService.release_lock(cell_address)
            
    except Exception as e:
        return False, str(e)

async def is_cell_free(cell_address: str) -> tuple[bool, str, str]:
    """
    Проверяет, свободна ли ячейка
    Возвращает (свободна ли, текущее значение если занято, сообщение об ошибке)
    """
    try:
        # Читаем ячейку
        result = await google_sheets_service.get_data(SHEET_NAME, cell_address)
        
        if not result:
            return True, "", ""
        
        if not result[0]:
            return True, "", ""
        
        value = result[0][0] if result[0] else ""
        if not value or not value.strip():
            return True, "", ""
        
        return False, value.strip(), ""
        
    except Exception as e:
        return False, "", f"Ошибка проверки ячейки: {str(e)}"

async def get_occupied_times_for_day(day: str) -> list[str]:
    """Получает список занятых времен для указанного дня"""
    try:
        occupied_times = []
        
        for time_slot, _ in TIME_SLOTS:
            cell_address, _ = get_cell_address(day, time_slot)
            if not cell_address:
                continue
                
            try:
                result = await google_sheets_service.get_data(SHEET_NAME, cell_address)
                if result and result[0] and result[0][0] and result[0][0].strip():
                    occupied_times.append(time_slot)
            except:
                continue
        
        return occupied_times
        
    except Exception as e:
        print(f"Ошибка при получении занятых времен: {e}")
        return []