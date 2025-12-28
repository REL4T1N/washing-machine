from .common import router as common_router
from .booking.commands import router as booking_commands_router
from .booking.callbacks import router as booking_callbacks_router

routers = [
    common_router,
    booking_commands_router,
    booking_callbacks_router,
]