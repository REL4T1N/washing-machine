from aiogram.fsm.state import State, StatesGroup

class BookingState(StatesGroup):
    choosing_day = State()
    choosing_time = State()
    entering_name = State()