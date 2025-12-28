from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.constants import DAYS_OF_WEEK, TIME_SLOTS

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
        builder.row(InlineKeyboardButton(text=day, callback_data=f"day_{day}"))
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    return builder.as_markup()

def get_times_keyboard(day: str, occupied_times: list[str] = None) -> InlineKeyboardMarkup:
    """Клавиатура для выбора времени с проверкой занятости"""
    builder = InlineKeyboardBuilder()
    
    occupied_times = occupied_times or []
    
    for time_text, time_code in TIME_SLOTS:
        if time_text in occupied_times:
            builder.row(InlineKeyboardButton(text=f"❌ {time_text} (занято)", callback_data="time_occupied"))
        else:
            builder.row(InlineKeyboardButton(text=f"✅ {time_text}", callback_data=f"time_{time_code}_{day}"))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад к выбору дня", callback_data="back_to_days"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    return builder.as_markup()