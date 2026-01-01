from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.constants import DAYS_OF_WEEK, TIME_SLOTS

from utils.date_helpers import get_formatted_date_for_day

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
    
    for day in DAYS_OF_WEEK:
        date_str = get_formatted_date_for_day(day)
        button_text = f"{day} ({date_str})"
        builder.row(InlineKeyboardButton(text=button_text, callback_data=f"day_{day}"))
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    return builder.as_markup()

def get_times_keyboard(day: str, target_date: str, free_times: list[str]) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора времени
    Показываем ТОЛЬКО свободные слоты на указанную дату
    
    Аргументы:
    - day: день недели ('Пн', 'Вт'...)
    - target_date: дата в формате 'дд.мм'
    - free_times: список времен, которые СВОБОДНЫ на эту дату
    """

    builder = InlineKeyboardBuilder()
    
    if not free_times:
        # Если нет свободных слотов
        builder.row(InlineKeyboardButton(
            text="❌ Нет свободных слотов", 
            callback_data="no_slots"
        ))
    else:
        for time_text, time_code in TIME_SLOTS:
            if time_text in free_times:
                # Только свободные слоты
                builder.row(InlineKeyboardButton(
                    text=f"✅ {time_text}", 
                    callback_data=f"time_{time_code}_{day}"
                ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад к выбору дня", callback_data="back_to_days"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    return builder.as_markup()