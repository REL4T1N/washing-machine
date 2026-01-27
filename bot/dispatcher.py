from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

def create_dispatcher() -> Dispatcher:
    """
    Создает и настраивает экземпляр Dispatcher.
    
    Returns:
        Dispatcher: Корневой роутер с поддержкой FSM в памяти.
    """
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    return dp