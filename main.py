import asyncio
import logging
import sys

from bot.bot import create_bot
from bot.dispatcher import create_dispatcher

from config.settings import google_settings, settings
from config.logging_config import setup_logging

from handlers import setup_routers

from services.google_sheets import GoogleSheetsService
from services.storage import UserStorage
from services.booking_service import BookingService


logger = logging.getLogger(__name__)

async def on_shutdown(storage: UserStorage):
    """
    Действия при завершении работы бота.
    
    Args:
        dispatcher: Экземпляр диспетчера.
        storage: Хранилище пользователей для вывода финальной статистики.
    """
    logger.info("Завершение работы бота...")
    
    # Вывод статистики перед завершением
    count = storage.get_users_count()
    logger.info(f"Сохранено {count} пользователей в хранилище")
        
    logger.info("Бот успешно остановлен")

async def main():
    """Основная функция инициализации и запуска polling."""
    
    # 1. Настройка логирования
    setup_logging()

    # 2. Инициализация Bot и Dispatcher
    bot = create_bot()
    dp = create_dispatcher()

    # 3. Инициализация сервисов (Dependency Injection)
    logger.info("Инициализация сервисов...")
    storage = UserStorage(filename="data/users_data.json")
    await storage.load()

    try:
        gs_service = GoogleSheetsService(
            spreadsheet_id=google_settings.spreadsheet_id,
            credentials_path=google_settings.service_account_file
        )
    except Exception as e:
        logger.critical(f"Не удалось инициализировать GoogleSheetsService: {e}")
        sys.exit(1) # Если нет подключения к таблице, бот бесполезен

    booking_service = BookingService(
        gs_service=gs_service,
        user_storage=storage,
        sheet_name=google_settings.sheet_name,
        lock_timeout=settings.lock_timeout
    )

    # 4. Прокидываем сервисы в middleware (workflow_data)
    dp["bot"] = bot
    dp["storage"] = storage
    dp["booking_service"] = booking_service
    dp["google_settings"] = google_settings
    dp["gs_service"] = gs_service 

    # 5. Настройка и регистрация роутеров
    setup_routers(dp, storage)

    # 6. Регистрация shutdown-хука
    dp.shutdown.register(on_shutdown)

    logger.info("🚀 Бот запускается...")
    logger.info(f"Загружено {storage.get_users_count()} пользователей из хранилища.")

    # Пропускаем накопившиеся апдейты и запускаем polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        # Гарантированное закрытие сессии бота
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Бот остановлен по запросу пользователя")
    except Exception as e:
        logging.critical(f"❌ Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)