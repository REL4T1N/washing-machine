# handlers/__init__.py (ФИНАЛЬНАЯ ПРОСТАЯ ВЕРСИЯ)
from aiogram import Dispatcher
from aiogram.filters import Command

from services.storage import UserStorage
from utils.filters import IsNamedUser

# Импортируем все наши роутеры
from .common import router as common_router
from .errors import router as errors_router
from .booking.commands import router as booking_commands_router
from .booking.callbacks import router as booking_callbacks_router
from .booking.management import router as booking_management_router
from .user_commands import router as user_commands_router

def setup_routers(dp: Dispatcher, storage: UserStorage):
    """
    Настраивает и подключает все роутеры проекта.
    """
    
    # 1. Создаем экземпляр нашего фильтра
    named_user_filter = IsNamedUser(storage=storage)

    # 2. Настраиваем фильтры для отдельных роутеров ПЕРЕД их подключением.
    # Это просто и понятно: "для этого роутера действуют такие правила".
    
    booking_commands_router.message.filter(named_user_filter)
    booking_management_router.message.filter(named_user_filter)
    booking_management_router.callback_query.filter(named_user_filter)

    # Отдельно настраиваем фильтр для команды /help в общем роутере
    from .common import cmd_help
    common_router.message.register(cmd_help, Command("help"), named_user_filter)
    
    # Настраиваем "блокирующий" фильтр для роутера ошибок
    errors_router.message.filter(~named_user_filter)

    # 3. Собираем роутеры в список в правильном порядке
    # (как у тебя и было)
    routers_list = [
        common_router,
        user_commands_router, # Команда /name должна быть доступна всем
        booking_commands_router,
        booking_callbacks_router,
        booking_management_router,
        errors_router, # Роутер ошибок - в самом конце
    ]

    # 4. Подключаем все роутеры из списка к диспетчеру
    dp.include_routers(*routers_list)