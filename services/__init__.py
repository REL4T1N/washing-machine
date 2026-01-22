from .booking_service import BookingService
from .google_sheets import GoogleSheetsService
from .storage import UserStorage

# Это позволит другим модулям делать так:
# from services import BookingService, UserStorage
# что довольно удобно.