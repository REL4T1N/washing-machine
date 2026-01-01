import asyncio
import logging
import signal
import sys


from bot.bot import bot
from bot.dispatcher import dp

# Хэндлеры
from handlers import routers

from services.storage import user_storage

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"Получен сигнал {signum}, завершаем работу...")
    sys.exit(0)

async def on_shutdown():
    """Функция, выполняемая при завершении работы бота"""
    logger.info("Завершение работы бота...")
    
    # Выводим статистику перед завершением
    count = user_storage.get_users_count()
    logger.info(f"Сохранено {count} пользователей в хранилище")
    
    # Для JSON хранилища данные уже сохранены автоматически
    # Но можно принудительно вызвать сохранение если нужно:
    # user_storage._save_to_file()
    
    logger.info("Бот успешно остановлен")

async def main():
    """Основная функция запуска бота"""
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Регистрация роутеров
    for router in routers:
        dp.include_router(router)
    # dp.include_router(errors_router)  # Должен быть последним!
    
    logger.info("🚀 Бот запускается...")

    count = user_storage.get_users_count()
    logger.info(f"Бот запущен. Загружено {count} пользователей из хранилища")
    
    try:
        # asyncio.create_task(cleanup_user_cache())
        # Запуск бота
        await dp.start_polling(bot)
    finally:
        # Гарантированное выполнение при завершении
        await on_shutdown()



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Бот остановлен по запросу пользователя")
    except Exception as e:
        logger.error(f"❌ Ошибка при работе бота: {e}")
        sys.exit(1)