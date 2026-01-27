from aiogram.fsm.state import State, StatesGroup

class BookingState(StatesGroup):
    choosing_day = State()   # Выбор дня недели
    choosing_time = State()  # Выбор временного интервала
