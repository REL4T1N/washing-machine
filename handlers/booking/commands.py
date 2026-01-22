from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.inline import get_main_menu_keyboard

from utils.formatters import format_washing_schedule_simple, split_message
# from utils.filters import IsNamedUser

from services.booking_service import BookingService

router = Router()

@router.message(Command("table"))#, IsNamedUser())
async def get_table(
    message: Message, 
    state: FSMContext,
    booking_service: BookingService,
):
    """Обработчик команды /table - отображение таблицы"""
    await show_table(message, state, booking_service)

async def show_table(
    message: Message, 
    state: FSMContext, 
    booking_service: BookingService,
    is_update: bool = False, 
    callback: CallbackQuery = None,
):
    """Показывает таблицу (используется и для команды, и для обновления)"""
    try:
        result = await booking_service.get_table_data(force_refresh=is_update)
        
        if not result or not result[0]:
            text = "📭 Таблица пуста"
        else:
            text = format_washing_schedule_simple(result)
        
        markup = get_main_menu_keyboard()

        # Разбиваем длинное сообщение
        if len(text) > 4000:
            messages = split_message(text, 4000)
            for i, msg in enumerate(messages):
                if i == len(messages) - 1:
                    if is_update and callback:
                        await callback.message.edit_text(text=msg, parse_mode="HTML", reply_markup=markup)
                        await callback.answer("✅ Данные обновлены", show_alert=False)
                    else:
                        await message.answer(text=msg, parse_mode="HTML", reply_markup=markup)
                else:
                    await message.answer(text=msg, parse_mode="HTML")
            await state.clear()
            return

        if is_update and callback:
            try:
                await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=markup)
                await callback.answer("✅ Данные обновлены", show_alert=False)
            except Exception as e:
                if "message is not modified" in str(e):
                    await callback.answer("✅ Данные уже актуальны", show_alert=False)
                else:
                    # Если нельзя отредактировать (старое сообщение), шлем новое
                    await callback.message.answer(text=text, parse_mode="HTML", reply_markup=markup)
                    await callback.answer()
        else:
            await message.answer(text=text, parse_mode="HTML", reply_markup=markup)
        
        await state.clear()
    
    except Exception as e:
        error_text = f"❌ Ошибка при чтении: {str(e)[:100]}"
        if is_update and callback:
            await callback.message.edit_text(text=error_text, reply_markup=get_main_menu_keyboard())
        else:
            await message.answer(text=error_text, reply_markup=get_main_menu_keyboard())
        await state.clear()
