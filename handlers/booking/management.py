from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from services.storage import UserStorage
from services.booking_service import BookingService

from keyboards.inline import get_user_bookings_keyboard, get_delete_confirm_keyboard, get_main_menu_keyboard

from utils.helpers import get_human_readable_slot

router = Router()

@router.message(Command("bookings"))
async def cmd_bookings(
    message: Message, 
    storage: UserStorage,
    booking_service: BookingService,
):
    """Точка входа через команду"""
    msg = await message.answer("🔄 Загружаю актуальные данные...")
    await show_bookings_menu(message.from_user.id, msg, storage, booking_service)

@router.callback_query(F.data == "my_bookings")
async def bookings_callback(
    callback: CallbackQuery,
    storage: UserStorage,
    booking_service: BookingService,
):
    """Точка входа через кнопку (если добавишь её в меню)"""
    await callback.answer("🔄 Синхронизация...")
    await show_bookings_menu(callback.from_user.id, callback.message, storage, booking_service)

@router.callback_query(F.data == "back_to_bookings")
async def back_to_bookings_handler(
    callback: CallbackQuery,
    storage: UserStorage,
    booking_service: BookingService,    
):
    """Вернуться к списку (при отмене удаления)"""
    await show_bookings_menu(callback.from_user.id, callback.message, storage, booking_service)

async def show_bookings_menu(
    user_id: int, 
    message_obj: Message,
    storage: UserStorage,
    booking_service: BookingService, 
    page: int = 0,
):
    """
    Общая функция показа меню:
    1. Грузит таблицу
    2. Синхронизирует
    3. Рисует меню
    """
    try:
        # 1. Получаем таблицу с принудительным обновлением (ОДИН ЗАПРОС)
        table_data = await booking_service.get_table_data(force_refresh=True)
        
        # 2. Синхронизируем (чистим мусор)
        user_points = await storage.sync_user_bookings(user_id, table_data)
        
        if not user_points:
            text = "📂 <b>У вас нет активных записей.</b>\nВоспользуйтесь командой /table или кнопкой 'Записаться'."
            if isinstance(message_obj, Message):
                # Если это новое сообщение, нужно проверить, можно ли его редактировать
                # Но проще отправить новое, если текст сильно отличается, или отредактировать
                await message_obj.edit_text(text, parse_mode="HTML", reply_markup=get_main_menu_keyboard())
            return

        # Превращаем dict в список для сортировки
        # { "B2": "19.01", "C3": "20.01" }
        bookings_list = []
        for cell, date in user_points.items():
            bookings_list.append((cell, date))
        
        # Сортируем по дате (просто лексикографически по строке даты пока сойдет, или можно парсить)
        bookings_list.sort(key=lambda x: x[1])

        text = "📋 <b>Ваши активные записи:</b>\n<i>Нажмите на запись для управления</i>"
        markup = get_user_bookings_keyboard(bookings_list, page)

        await message_obj.edit_text(text=text, parse_mode="HTML", reply_markup=markup)
        
    except Exception as e:
        error_text = f"❌ Ошибка при загрузке записей: {str(e)}"
        await message_obj.edit_text(text=error_text)

# --- ПАГИНАЦИЯ ---
@router.callback_query(F.data.startswith("bookings_page_"))
async def bookings_pagination(
    callback: CallbackQuery,
    storage: UserStorage,
    booking_service: BookingService,       
):
    page = int(callback.data.split("_")[2])
    # Тут не делаем force_refresh, просто берем из памяти, так как юзер только что синхронизировался
    # Или для надежности можно вызвать show_bookings_menu снова (там есть кэш)
    await show_bookings_menu(callback.from_user.id, callback.message, storage, booking_service, page)
    await callback.answer()

# --- ВЫБОР ЗАПИСИ ДЛЯ УДАЛЕНИЯ ---
@router.callback_query(F.data.startswith("manage_booking_"))
async def manage_booking_handler(
    callback: CallbackQuery,
    storage: UserStorage,
    booking_service: BookingService,   
):
    cell_address = callback.data.replace("manage_booking_", "")
    
    # Проверим, существует ли запись еще
    owner = storage.get_owner_by_cell(cell_address)
    if not owner or str(owner) != str(callback.from_user.id):
        await callback.answer("❌ Запись устарела или не найдена", show_alert=True)
        await show_bookings_menu(callback.from_user.id, callback.message, storage, booking_service)
        return

    slot_info = get_human_readable_slot(cell_address)
    
    await callback.message.edit_text(
        text=f"🗑️ <b>Удаление записи</b>\n\n"
             f"Вы действительно хотите отменить запись:\n"
             f"📍 <b>{slot_info}</b>?",
        parse_mode="HTML",
        reply_markup=get_delete_confirm_keyboard(cell_address)
    )
    await callback.answer()

# --- ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ---
@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_handler(
    callback: CallbackQuery,
    storage: UserStorage,
    booking_service: BookingService,       
):
    cell_address = callback.data.replace("confirm_delete_", "")
    
    await callback.message.edit_text("⏳ Удаляю запись...")
    
    success, msg = await booking_service.delete_booking(cell_address, callback.from_user.id)
    
    if success:
        await callback.answer("✅ Запись удалена")
        # Возвращаемся в меню (оно само обновится)
        await show_bookings_menu(callback.from_user.id, callback.message, storage, booking_service)
    else:
        await callback.message.edit_text(
            text=f"❌ Ошибка удаления: {msg}",
            reply_markup=get_main_menu_keyboard() # Или кнопка Назад
        )