from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

def create_dispatcher() -> Dispatcher:
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    return dp