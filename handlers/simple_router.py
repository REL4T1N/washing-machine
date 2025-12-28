import asyncio
import re
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional


from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем ваш сервис Google Sheets
from services.google_sheets import google_sheets_service
from config.config import SHEET_NAME

router = Router()

# --- Состояния для FSM ---
class BookingState(StatesGroup):
    choosing_day = State()
    choosing_time = State()
    entering_name = State()

# --- Блокировки для предотвращения конкурентных записей ---
temporary_locks: Dict[str, float] = {}

# --- Глобальные переменные для кэширования ---
# Храним: user_id -> (message_id, data_hash, original_text)
user_table_cache: Dict[int, Tuple[int, str, str]] = {}
# Храним последние данные таблицы для быстрого сравнения
last_table_data: Optional[List[List[str]]] = None
last_table_hash: Optional[str] = None


# --- Вспомогательные функции ---

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="update_list")
    )
    builder.row(
        InlineKeyboardButton(text="📝 Записаться", callback_data="write_me")
    )

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_days_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора дня недели"""
    builder = InlineKeyboardBuilder()
    
    days = [
        ("Пн", "day_Пн"),
        ("Вт", "day_Вт"), 
        ("Ср", "day_Ср"),
        ("Чт", "day_Чт"),
        ("Пт", "day_Пт"),
        ("Сб", "day_Сб"),
        ("Вс", "day_Вс")
    ]
    
    for day_text, callback_data in days:
        builder.row(InlineKeyboardButton(text=day_text, callback_data=callback_data))
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    return builder.as_markup()


def get_times_keyboard(day: str, occupied_times: List[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура для выбора времени с проверкой занятости"""
    builder = InlineKeyboardBuilder()
    
    # Список всех временных слотов в правильном формате
    # Используем простой формат для callback_data: time_8_9_Пн
    times = [
        ("8:00-9:00", "8_9"),
        ("10:00-11:00", "10_11"),
        ("12:00-13:00", "12_13"),
        ("14:00-15:00", "14_15"),
        ("16:00-17:00", "16_17"),
        ("18:00-19:00", "18_19"),
        ("20:00-21:00", "20_21"),
        ("22:00-23:00", "22_23"),
    ]
    
    occupied_times = occupied_times or []
    
    for time_text, time_code in times:
        if time_text in occupied_times:
            builder.row(InlineKeyboardButton(
                text=f"❌ {time_text} (занято)", 
                callback_data="time_occupied"
            ))
        else:
            # Формат: time_8_9_Пн (просто и однозначно)
            builder.row(InlineKeyboardButton(
                text=f"✅ {time_text}", 
                callback_data=f"time_{time_code}_{day}"
            ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад к выбору дня", callback_data="back_to_days"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    return builder.as_markup()


def split_message(text: str, max_length: int = 4000) -> List[str]:
    """Разбивает длинное сообщение на части"""
    messages = []
    while len(text) > max_length:
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = max_length
            
        messages.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    
    if text:
        messages.append(text)
    
    return messages


# --- Функции форматирования таблицы ---

def calculate_data_hash(data: List[List[str]]) -> str:
    """Вычисляет хеш данных таблицы для быстрого сравнения"""
    if not data:
        return "empty"
    
    # Создаем строковое представление данных
    data_str = ""
    for row in data:
        data_str += "|".join(str(cell) for cell in row) + "\n"
    
    # Вычисляем MD5 хеш
    return hashlib.md5(data_str.encode()).hexdigest()

def format_washing_schedule_simple(data: List[List[str]]) -> str:
    """Упрощенное форматирование расписания"""
    if len(data) < 2:
        return "📭 Таблица пуста"
    
    lines = ["📅 <b>РАСПИСАНИЕ СТИРАЛЬНЫХ МАШИН</b>\n"]
    
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    for day_idx, day_name in enumerate(days):
        name_col_idx = day_idx * 2 + 1
        
        if day_idx * 2 >= len(data[0]):
            continue
        
        day_lines = [f"\n<b>{day_name}</b>", "─" * 20]
        
        for time_row_idx in range(1, min(9, len(data))):
            time_slot = data[time_row_idx][0] if data[time_row_idx] else ""
            
            booking = "свободно"
            if (len(data[time_row_idx]) > name_col_idx and 
                data[time_row_idx][name_col_idx] and 
                data[time_row_idx][name_col_idx].strip()):
                booking = data[time_row_idx][name_col_idx].strip()
            
            if time_slot:
                status = "🔴" if booking != "свободно" else "🟢"
                day_lines.append(f"{status} <b>{time_slot}</b>: {booking}")
        
        lines.extend(day_lines)
    
    return "\n".join(lines)


# --- Функции работы с Google Sheets ---

async def is_cell_free(cell_address: str) -> Tuple[bool, str, str]:
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


async def acquire_lock(cell_address: str, timeout: int = 10) -> bool:
    """Пытается получить блокировку для ячейки"""
    current_time = time.time()
    
    # Очищаем устаревшие блокировки
    expired_keys = [k for k, v in temporary_locks.items() if current_time - v > timeout]
    for key in expired_keys:
        temporary_locks.pop(key, None)
    
    # Проверяем, заблокирована ли ячейка
    if cell_address in temporary_locks:
        lock_age = current_time - temporary_locks[cell_address]
        if lock_age < timeout:
            return False
    
    # Устанавливаем блокировку
    temporary_locks[cell_address] = current_time
    return True


async def release_lock(cell_address: str):
    """Освобождает блокировку ячейки"""
    temporary_locks.pop(cell_address, None)


def get_cell_address(day: str, time_slot: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Определяет адрес ячейки по дню и времени
    Возвращает (адрес_ячейки, строка) или (None, None) при ошибке
    """
    # Маппинг дня на колонку
    day_to_column = {
        "Пн": "B", "Вт": "D", "Ср": "F", "Чт": "H",
        "Пт": "J", "Сб": "L", "Вс": "N",
    }
    
    # Маппинг времени на строку
    time_to_row = {
        "8:00-9:00": 2,
        "10:00-11:00": 3,
        "12:00-13:00": 4,
        "14:00-15:00": 5,
        "16:00-17:00": 6,
        "18:00-19:00": 7,
        "20:00-21:00": 8,
        "22:00-23:00": 9,
    }
    
    column = day_to_column.get(day)
    row = time_to_row.get(time_slot)
    
    if not column or not row:
        return None, None
    
    return f"{column}{row}", row


async def write_to_sheet_with_lock(day: str, time_slot: str, value: str) -> Tuple[bool, str]:
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
        lock_acquired = await acquire_lock(cell_address)
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
            await release_lock(cell_address)
            
    except Exception as e:
        return False, str(e)


async def get_occupied_times_for_day(day: str) -> List[str]:
    """Получает список занятых времен для указанного дня"""
    try:
        occupied_times = []
        
        # Проходим по всем временным слотам
        time_slots = [
            "8:00-9:00", "10:00-11:00", "12:00-13:00", "14:00-15:00",
            "16:00-17:00", "18:00-19:00", "20:00-21:00", "22:00-23:00"
        ]
        
        for time_slot in time_slots:
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


def validate_name_date_input(text: str) -> Tuple[bool, str, str, str]:
    """
    Проверяет ввод имени и даты
    Возвращает (корректно ли, имя, дата, сообщение об ошибке)
    """
    text = text.strip()
    
    if len(text) < 3:
        return False, "", "", "Слишком короткий ввод. Нужно: Имя дд.мм"
    
    parts = text.split()
    
    if len(parts) < 2:
        return False, "", "", "Нужно ввести имя и дату через пробел"
    
    name = " ".join(parts[:-1])
    date_str = parts[-1]
    
    if len(name) < 2:
        return False, "", "", "Имя должно быть минимум 2 символа"
    
    # Проверяем дату
    date_pattern = r'^\d{1,2}\.\d{1,2}$'
    if not re.match(date_pattern, date_str):
        return False, "", "", "Неверный формат даты. Используйте: дд.мм (например: 25.12)"
    
    try:
        day, month = map(int, date_str.split('.'))
        
        if month < 1 or month > 12:
            return False, "", "", "Месяц должен быть от 1 до 12"
        
        if day < 1 or day > 31:
            return False, "", "", "День должен быть от 1 до 31"
        
        if month == 2 and day > 29:
            return False, "", "", "В феврале максимум 29 дней"
        
        if month in [4, 6, 9, 11] and day > 30:
            return False, "", "", f"В {month} месяце максимум 30 дней"
            
    except ValueError:
        return False, "", "", "Ошибка в формате даты"
    
    formatted_date = f"{day:02d}.{month:02d}"
    
    return True, name, formatted_date, ""


# --- Обработчики команд ---

@router.message(Command("table"))
async def get_table(mes: Message, state: FSMContext):
    """Обработчик команды /table - отображение таблицы"""
    await show_table(mes, state)


async def show_table(message: Message, state: FSMContext, is_update: bool = False, callback: CallbackQuery = None):
    """Показывает таблицу (используется и для команды, и для обновления)"""
    global last_table_data, last_table_hash
    
    try:
        range_input = "A1:N9"
        
        # Если у нас есть кэшированные данные и это обновление, 
        # проверяем сначала локальный кэш перед запросом к Google Sheets
        if is_update and last_table_data is not None:
            # Используем кэшированные данные для быстрой проверки
            cached_text = format_washing_schedule_simple(last_table_data)
            
            # Делаем запрос к Google Sheets для получения актуальных данных
            result = await google_sheets_service.get_data(SHEET_NAME, range_input)
            
            if result:
                current_hash = calculate_data_hash(result)
                
                # Если данные не изменились
                if current_hash == last_table_hash:
                    if callback:
                        await callback.answer("✅ Данные уже актуальны", show_alert=False)
                    return
                
                # Данные изменились, обновляем кэш
                last_table_data = result
                last_table_hash = current_hash
                text = format_washing_schedule_simple(result)
            else:
                text = "📭 Таблица пуста"
        else:
            # Первый запрос или команда /table
            result = await google_sheets_service.get_data(SHEET_NAME, range_input)
            
            if not result or not result[0]:
                text = "📭 Таблица пуста"
            else:
                text = format_washing_schedule_simple(result)
                # Сохраняем в кэш
                last_table_data = result
                last_table_hash = calculate_data_hash(result)
        
        # Разбиваем длинное сообщение если нужно
        if len(text) > 4000:
            messages = split_message(text, 4000)
            for i, msg in enumerate(messages):
                if i == len(messages) - 1:
                    if is_update and callback:
                        try:
                            await callback.message.edit_text(
                                text=msg, 
                                parse_mode="HTML", 
                                reply_markup=get_main_menu_keyboard()
                            )
                            # Сохраняем в кэш пользователя
                            if callback.from_user:
                                user_table_cache[callback.from_user.id] = (
                                    callback.message.message_id,
                                    last_table_hash,
                                    text
                                )
                        except Exception as e:
                            await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)
                    else:
                        sent_message = await message.answer(
                            text=msg, 
                            parse_mode="HTML", 
                            reply_markup=get_main_menu_keyboard()
                        )
                        # Сохраняем в кэш пользователя
                        if message.from_user:
                            user_table_cache[message.from_user.id] = (
                                sent_message.message_id,
                                last_table_hash,
                                text
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
                # Обновляем кэш пользователя
                if callback.from_user:
                    user_table_cache[callback.from_user.id] = (
                        callback.message.message_id,
                        last_table_hash,
                        text
                    )
                await callback.answer("✅ Данные обновлены", show_alert=False)
            except Exception as e:
                if "message is not modified" in str(e):
                    await callback.answer("✅ Данные уже актуальны", show_alert=False)
                else:
                    # Отправляем новое сообщение
                    sent_message = await callback.message.answer(
                        text=text,
                        parse_mode="HTML",
                        reply_markup=get_main_menu_keyboard()
                    )
                    if callback.from_user:
                        user_table_cache[callback.from_user.id] = (
                            sent_message.message_id,
                            last_table_hash,
                            text
                        )
                    await callback.answer("✅ Данные обновлены (отправлено новое сообщение)", show_alert=False)
        else:
            sent_message = await message.answer(
                text=text,
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
            # Сохраняем в кэш пользователя
            if message.from_user:
                user_table_cache[message.from_user.id] = (
                    sent_message.message_id,
                    last_table_hash,
                    text
                )
        
        await state.clear()
    
    except Exception as e:
        error_text = f"❌ Ошибка при чтении: {str(e)[:100]}"
        if is_update and callback:
            try:
                await callback.message.edit_text(
                    text=error_text,
                    reply_markup=get_main_menu_keyboard()
                )
            except:
                await callback.message.answer(
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

# Функция для принудительного обновления кэша при записи
async def invalidate_table_cache():
    """Инвалидирует кэш таблицы (вызывается после записи)"""
    global last_table_data, last_table_hash
    last_table_data = None
    last_table_hash = None
    print("Кэш таблицы сброшен")

# --- Обработчики callback-запросов ---

@router.callback_query(F.data == "update_list")
async def update_table_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки обновления"""
    await callback.answer("🔄 Проверяю обновления...", show_alert=False)
    await show_table(callback.message, state, is_update=True, callback=callback)


@router.callback_query(F.data == "write_me")
async def write_me_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки записи"""
    await callback.answer("📝 Запуск процесса записи...")
    
    await state.set_state(BookingState.choosing_day)
    
    await callback.message.edit_text(
        text="📅 Выберите день недели:",
        parse_mode="HTML",
        reply_markup=get_days_keyboard()
    )


@router.callback_query(F.data.startswith("day_"))
async def choose_day_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора дня"""
    selected_day = callback.data.replace("day_", "")
    
    if selected_day not in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        await callback.answer("❌ Ошибка выбора дня")
        return
    
    await state.update_data(selected_day=selected_day)
    await state.set_state(BookingState.choosing_time)
    
    occupied_times = await get_occupied_times_for_day(selected_day)
    
    await callback.message.edit_text(
        text=f"📅 Выбран день: <b>{selected_day}</b>\n\n"
             f"Выберите свободное время (❌ - занято, ✅ - свободно):",
        parse_mode="HTML",
        reply_markup=get_times_keyboard(selected_day, occupied_times)
    )
    
    await callback.answer()


@router.callback_query(F.data == "time_occupied")
async def time_occupied_handler(callback: CallbackQuery):
    """Обработчик нажатия на занятое время"""
    await callback.answer("❌ Это время уже занято! Выберите другое время.", show_alert=True)


@router.callback_query(F.data.startswith("time_"))
async def choose_time_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора времени"""
    try:
        # Формат callback_data: time_8_9_Пн
        # Разделяем по подчеркиваниям
        parts = callback.data.split("_")
        
        if len(parts) != 4:
            await callback.answer("❌ Ошибка формата данных")
            return
        
        # parts[0] = "time"
        start_hour = parts[1]  # "8"
        end_hour = parts[2]    # "9"
        selected_day = parts[3]  # "Пн"
        
        # Форматируем время в читаемый вид
        time_str = f"{start_hour}:00-{end_hour}:00"
        
        await state.update_data(
            selected_time=time_str,
            selected_day=selected_day
        )
        await state.set_state(BookingState.entering_name)
        
        today = datetime.now()
        date_suggestion = today.strftime("%d.%m")
        
        await callback.message.edit_text(
            text=f"📝 <b>Запись на:</b>\n"
                 f"📅 День: <b>{selected_day}</b>\n"
                 f"⏰ Время: <b>{time_str}</b>\n\n"
                 f"Введите ваше имя и дату в формате:\n"
                 f"<code>Имя дд.мм</code>\n\n"
                 f"<i>Например: Иван {date_suggestion}</i>\n"
                 f"<i>или: Мария 25.12</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        
        await callback.answer()
        
    except Exception as e:
        print(f"DEBUG Ошибка в choose_time_handler: {e}, callback_data: {callback.data}")
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)


@router.callback_query(F.data == "back_to_days")
async def back_to_days_handler(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору дня"""
    await state.set_state(BookingState.choosing_day)
    await callback.message.edit_text(
        text="📅 Выберите день недели:",
        parse_mode="HTML",
        reply_markup=get_days_keyboard()
    )


@router.message(BookingState.entering_name)
async def enter_name_handler(message: Message, state: FSMContext):
    """Обработчик ввода имени и даты"""
    user_input = message.text.strip()
    
    print(f"DEBUG: Введены данные: '{user_input}'")
    
    is_valid, name, date, error_msg = validate_name_date_input(user_input)
    
    if not is_valid:
        await message.answer(
            text=f"❌ {error_msg}\n\n"
                 f"Попробуйте еще раз в формате: <code>Имя дд.мм</code>\n"
                 f"<i>Например: Иван 25.12</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    day = data.get('selected_day')
    time_slot = data.get('selected_time')
    
    print(f"DEBUG: Получены из состояния - день: '{day}', время: '{time_slot}'")
    
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
            
            # Сбрасываем кэш таблицы после успешной записи
            await invalidate_table_cache()
            
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
        print(f"DEBUG: Ошибка при записи в таблицу: {e}")
        await processing_msg.edit_text(
            text=f"❌ <b>Критическая ошибка:</b>\n{str(e)}\n\n"
                 f"Пожалуйста, обратитесь к администратору.",
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()


@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены"""
    await state.clear()
    await callback.message.edit_text(
        text="❌ Операция отменена.",
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer("Отменено")


# --- Дополнительные команды для отладки ---

@router.message(Command("help"))
async def help_command(message: Message):
    """Помощь по использованию бота"""
    help_text = (
        "🤖 <b>Бот для записи на стиральные машины</b>\n\n"
        "📋 <b>Доступные команды:</b>\n"
        "/table - Показать расписание\n"
        "/help - Эта справка\n\n"
        "📝 <b>Как записаться:</b>\n"
        "1. Нажмите 'Записаться' под расписанием\n"
        "2. Выберите день недели\n"
        "3. Выберите свободное время\n"
        "4. Введите имя и дату в формате: <code>Имя дд.мм</code>\n\n"
        "🔄 <b>Обновление:</b>\n"
        "Нажмите 'Обновить', чтобы увидеть актуальное расписание\n\n"
        "❌ <b>Отмена:</b>\n"
        "В любой момент можно нажать 'Отмена' для прерывания"
    )
    
    await message.answer(text=help_text, parse_mode="HTML")

# Команда для принудительного сброса кэша (для админов)
@router.message(Command("clear_cache"))
async def clear_cache_command(message: Message):
    """Очистить кэш таблицы"""
    global last_table_data, last_table_hash, user_table_cache
    
    last_table_data = None
    last_table_hash = None
    user_table_cache.clear()
    
    await message.answer("✅ Кэш таблицы очищен")


# Команда для просмотра статистики кэша
@router.message(Command("cache_stats"))
async def cache_stats_command(message: Message):
    """Показать статистику кэша"""
    stats_text = (
        f"📊 <b>Статистика кэша:</b>\n\n"
        f"• Данные таблицы в кэше: {'Да' if last_table_data else 'Нет'}\n"
        f"• Хеш таблицы: {last_table_hash[:10] if last_table_hash else 'Нет'}\n"
        f"• Пользователей в кэше: {len(user_table_cache)}\n"
        f"• ID пользователей: {', '.join(map(str, list(user_table_cache.keys())[:5]))}"
        f"{'...' if len(user_table_cache) > 5 else ''}"
    )
    
    await message.answer(stats_text, parse_mode="HTML")


@router.message(Command("check_cell"))
async def check_cell_command(message: Message):
    """Проверить конкретную ячейку (для отладки)"""
    try:
        if len(message.text.split()) < 2:
            await message.answer("❌ Используйте: /check_cell A1")
            return
        
        cell = message.text.split()[1]
        result = await google_sheets_service.get_data(SHEET_NAME, cell)
        
        if not result or not result[0]:
            await message.answer(f"✅ Ячейка <b>{cell}</b> пуста")
        else:
            value = result[0][0] if result[0] else ""
            await message.answer(f"📝 Ячейка <b>{cell}</b>: <code>{value}</code>")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("clear_cell"))
async def clear_cell_command(message: Message):
    """Очистить ячейку (только для админов)"""
    # Здесь можно добавить проверку на админа
    try:
        if len(message.text.split()) < 2:
            await message.answer("❌ Используйте: /clear_cell A1")
            return
        
        cell = message.text.split()[1]
        success = await google_sheets_service.write_value(SHEET_NAME, cell, "")
        
        if success:
            await message.answer(f"✅ Ячейка <b>{cell}</b> очищена")
        else:
            await message.answer(f"❌ Ошибка при очистке ячейки")
    
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

# Периодическая очистка устаревших записей в кэше пользователей
async def cleanup_user_cache():
    """Периодически очищает кэш пользователей"""
    while True:
        await asyncio.sleep(3600)  # Каждый час
        # Можно добавить логику очистки старых записей
        # Например, очищать записи старше 24 часов
        current_time = time.time()
        expired_users = []
        for user_id, (_, _, cache_time) in user_table_cache.items():
            if current_time - cache_time > 86400:  # 24 часа
                expired_users.append(user_id)
        
        for user_id in expired_users:
            user_table_cache.pop(user_id, None)
        
        if expired_users:
            print(f"[CACHE] Очищено {len(expired_users)} устаревших записей")