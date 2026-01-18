from .common import router as common_router
from .errors import router as errors_router
from .booking.commands import router as booking_commands_router
from .booking.callbacks import router as booking_callbacks_router
from .booking.management import router as booking_management_router
from .user_commands import router as user_commands_router

routers = [
    common_router,
    booking_commands_router,
    booking_callbacks_router,
    booking_management_router,
    user_commands_router,
    errors_router,
]