from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from handlers.booking.commands import show_table

from states.booking_states import BookingState

from keyboards.inline import get_days_keyboard, get_times_keyboard, get_main_menu_keyboard

from utils.date_helpers import get_date_for_day

from services.booking_service import BookingService
from services.storage import UserStorage

router = Router()

@router.callback_query(F.data == "update_list")
async def update_table_handler(
    callback: CallbackQuery, 
    state: FSMContext,
    booking_service: BookingService,
):
    """Обработчик кнопки обновления"""
    await callback.answer("🔄 Проверяю обновления...", show_alert=False)
    await show_table(callback.message, state, booking_service, is_update=True, callback=callback)

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
async def choose_day_handler(
    callback: CallbackQuery, 
    state: FSMContext,
    booking_service: BookingService,
):
    """Обработчик выбора дня"""
    selected_day = callback.data.replace("day_", "")
    
    if selected_day not in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]:
        await callback.answer("❌ Ошибка выбора дня")
        return
    
    target_date = get_date_for_day(selected_day)

    await state.update_data(selected_day=selected_day, target_date=target_date)
    await state.set_state(BookingState.choosing_time)
    
    free_times = await booking_service.get_free_slots_for_day(selected_day, target_date)
    
    await callback.message.edit_text(
        text=f"📅 Выбран день: <b>{selected_day}</b>\n"
             f"📆 Дата: <b>{target_date}</b>\n\n"
             f"Выберите свободное время:",
        parse_mode="HTML",
        reply_markup=get_times_keyboard(selected_day, target_date, free_times)
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("time_"))
async def choose_time_handler(
    callback: CallbackQuery, 
    state: FSMContext,
    booking_service: BookingService,
    storage: UserStorage,
):
    """Обработчик выбора времени"""
    try:
        # Формат callback_data: time_8_9_Пн
        parts = callback.data.split("_")
        
        if len(parts) != 4:
            await callback.answer("❌ Ошибка формата данных")
            return
        
        start_hour = parts[1]  # "8"
        end_hour = parts[2]    # "9"
        selected_day = parts[3]  # "Пн"
        
        time_slot = f"{start_hour}:00-{end_hour}:00"
        
        data = await state.get_data()
        target_date = data.get('target_date')
        
        # 1. Получаем имя пользователя
        user_id = callback.from_user.id
        user_data = storage.get_user(user_id)
        
        # Теоретически такого быть не должно из-за фильтров, но проверим
        if not user_data or not user_data.get("name"):
            await callback.answer("❌ Ошибка: У вас не установлено имя. Используйте /name", show_alert=True)
            await state.clear()
            return

        name = user_data.get("name")

        # 2. Визуальное подтверждение
        await callback.message.edit_text(
            text=f"⏳ Записываю...\n"
                 f"👤 <b>{name}</b>\n"
                 f"📅 {selected_day} {target_date}\n"
                 f"⏰ {time_slot}",
            parse_mode="HTML"
        )

        # 3. Попытка записи        
        success, error_msg = await booking_service.book_slot(
            user_id=user_id,
            day=selected_day,
            time_slot=time_slot,
            target_date=target_date,
        )

        if success:
            await callback.message.edit_text(
                text=f"✅ <b>Успешная запись!</b>\n\n"
                     f"👤 <b>{name}</b>\n"
                     f"📅 {selected_day} ({target_date})\n"
                     f"⏰ {time_slot}\n\n"
                     f"<i>Нажмите 'Обновить', чтобы увидеть себя в таблице.</i>",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                text=f"❌ <b>Не удалось записаться:</b>\n{error_msg}\n\n"
                     f"Попробуйте выбрать другое время.",
                parse_mode="HTML",
                reply_markup=get_main_menu_keyboard()
            )
        
        await state.clear()

    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)
        await state.clear()

@router.callback_query(F.data == "back_to_days")
async def back_to_days_handler(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору дня"""
    await state.set_state(BookingState.choosing_day)
    await callback.message.edit_text(
        text="📅 Выберите день недели:",
        parse_mode="HTML",
        reply_markup=get_days_keyboard()
    )

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

@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(
    callback: CallbackQuery, 
    state: FSMContext,
    booking_service: BookingService,
):
    """Возвращает пользователя в главное меню с таблицей"""
    # Сбрасываем возможные состояния
    await state.clear()
    
    await callback.answer("🏠 Главное меню")
    
    # Используем уже готовую функцию отображения таблицы
    # is_update=True позволяет отредактировать текущее сообщение, а не слать новое
    await show_table(callback.message, state, booking_service, is_update=True, callback=callback)