import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    """Настраивает логирование в консоль и в файл."""
    
    # Создаем директорию для логов, если ее нет
    import os
    if not os.path.exists('data'):
        os.makedirs('data')

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Получаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG) # Устанавливаем самый низкий уровень

    # 1. Обработчик для вывода в консоль (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) # Выводим в консоль только INFO и выше
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # 2. Обработчик для записи в файл
    # RotatingFileHandler автоматически будет создавать новые файлы логов, когда старый достигнет 5MB
    file_handler = RotatingFileHandler(
        'data/bot.log', 
        maxBytes=5*1024*1024, # 5 MB
        backupCount=2, 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG) # В файл пишем всё, начиная с DEBUG
    file_handler.setFormatter(logging.Formatter(log_format))

    # Добавляем обработчики к корневому логгеру
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.info("Система логирования настроена.")