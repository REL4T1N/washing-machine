import os
import sys
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Настраивает глобальную систему логирования.
    
    - DEBUG и выше: записывается в файл 'data/bot.log' (с ротацией).
    - INFO и выше: выводится в консоль (stdout).
    """
    
    # Создание директории для логов, если ее нет
    log_dir = 'data'
    log_file = os.path.join(log_dir, 'bot.log')

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 1. Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 2. Консольный обработчик (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO) 
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # 3. Файловый обработчик с ротацией (5MB, 2 старых лога)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024,
        backupCount=2, 
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.info("Система логирования настроена.")