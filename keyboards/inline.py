from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config.constants import DAYS_OF_WEEK, TIME_SLOTS

from utils.date_helpers import get_formatted_date_for_day
from utils.helpers import get_human_readable_slot


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="update_list")
    )
    builder.row(
        InlineKeyboardButton(text="📝 Записаться", callback_data="write_me")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings")
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
    """Клавиатура выбора времени, фильтрующая только доступные слоты."""
    builder = InlineKeyboardBuilder()
    
    if not free_times:
        builder.row(InlineKeyboardButton(
            text="❌ Нет свободных слотов", 
            callback_data="no_slots"
        ))
    else:
        for time_text, time_code in TIME_SLOTS:
            if time_text in free_times:
                builder.row(InlineKeyboardButton(
                    text=f"✅ {time_text}", 
                    callback_data=f"time_{time_code}_{day}"
                ))
    
    builder.row(InlineKeyboardButton(text="◀️ Назад к выбору дня", callback_data="back_to_days"))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    
    return builder.as_markup()

def get_user_bookings_keyboard(bookings_list: list, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура списка записей пользователя с пагинацией."""
    builder = InlineKeyboardBuilder()
    
    ITEMS_PER_PAGE = 6
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    current_page_items = bookings_list[start_idx:end_idx]
    
    for cell_addr, date_str in current_page_items:
        slot_text = get_human_readable_slot(cell_addr)
        btn_text = f"📅 {date_str} {slot_text}"
        
        builder.row(InlineKeyboardButton(text=btn_text, callback_data=f"manage_booking_{cell_addr}"))
    
    # Пагинация
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bookings_page_{page-1}"))
    
    if end_idx < len(bookings_list):
        pagination_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"bookings_page_{page+1}"))
        
    if pagination_buttons:
        builder.row(*pagination_buttons)
        
    builder.row(InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_main"))
    
    return builder.as_markup()

def get_delete_confirm_keyboard(cell_address: str) -> InlineKeyboardMarkup:
    """Подтверждение удаления конкретной записи."""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="🗑️ Да, удалить", callback_data=f"confirm_delete_{cell_address}"))
    builder.row(InlineKeyboardButton(text="🔙 Не удалять", callback_data="back_to_bookings"))
    
    return builder.as_markup()