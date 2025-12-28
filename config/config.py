import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Конфигурация Google Sheets
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = 'test-project-for-my-university-98454d99c7e1.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Настройки таблицы
SHEET_NAME = 'Лист1'  # Или другое название вашего листа

LOCK_TIMEOUT = 10