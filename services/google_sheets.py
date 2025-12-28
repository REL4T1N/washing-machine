import asyncio
import os
from typing import List, Optional, Any, Dict, Tuple
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.config import SPREADSHEET_ID, SERVICE_ACCOUNT_FILE, SCOPES


class GoogleSheetsService:
    """Сервис для работы с Google Sheets API"""
    
    def __init__(self):
        self.spreadsheet_id = SPREADSHEET_ID
        self.service = None
        
        # Получаем абсолютный путь к файлу сервисного аккаунта
        self.service_account_file = self._get_service_account_path(SERVICE_ACCOUNT_FILE)
        
        self._initialize()
    
    def _get_service_account_path(self, filename: str) -> str:
        """Получение абсолютного пути к файлу сервисного аккаунта"""
        # Проверяем, существует ли файл по относительному пути
        if os.path.exists(filename):
            return os.path.abspath(filename)
        
        # Проверяем в корневой директории проекта
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(project_root, filename)
        
        if os.path.exists(file_path):
            return file_path
        
        # Проверяем в директории config
        config_path = os.path.join(project_root, 'config', filename)
        if os.path.exists(config_path):
            return config_path
        
        # Если файл не найден, выбрасываем исключение с подсказкой
        raise FileNotFoundError(
            f"Файл сервисного аккаунта '{filename}' не найден.\n"
            f"Искал в:\n"
            f"1. {os.path.abspath(filename)}\n"
            f"2. {file_path}\n"
            f"3. {config_path}\n\n"
            f"Убедитесь, что файл находится в одной из этих директорий."
        )
    
    def _initialize(self):
        """Инициализация сервиса"""
        try:
            print(f"🔧 Загрузка файла сервисного аккаунта: {self.service_account_file}")
            
            if not os.path.exists(self.service_account_file):
                raise FileNotFoundError(f"Файл не найден: {self.service_account_file}")
            
            creds = Credentials.from_service_account_file(
                self.service_account_file,
                scopes=SCOPES
            )
            self.service = build('sheets', 'v4', credentials=creds)
            print(f"✅ Google Sheets API инициализирован")
            print(f"📊 Таблица ID: {SPREADSHEET_ID}")
        except FileNotFoundError as e:
            raise Exception(f"❌ Файл сервисного аккаунта не найден: {e}")
        except Exception as e:
            raise Exception(f"❌ Ошибка инициализации Google Sheets: {e}")
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Тестирование подключения к таблице"""
        try:
            info = await self.get_sheets_info()
            if info:
                sheets_count = len(info)
                sheet_names = ", ".join([sheet['title'] for sheet in info[:3]])
                if sheets_count > 3:
                    sheet_names += f" и еще {sheets_count - 3} листов"
                return True, f"✅ Подключено. Листы: {sheet_names}"
            return False, "❌ Не удалось получить информацию о листах"
        except Exception as e:
            return False, f"❌ Ошибка подключения: {str(e)}"
    
    async def get_data(
        self,
        sheet_name: str,
        range_a1: Optional[str] = None
    ) -> List[List[Any]]:
        """Получение данных из таблицы"""
        try:
            range_name = f"{sheet_name}!{range_a1}" if range_a1 else sheet_name
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name
                ).execute()
            )
            
            return result.get('values', [])
        except HttpError as e:
            raise Exception(f"Ошибка чтения данных: {e}")
    
    async def write_value(
        self,
        sheet_name: str,
        cell: str,
        value: Any
    ) -> bool:
        """Запись значения в ячейку"""
        try:
            range_name = f"{sheet_name}!{cell}"
            
            body = {'values': [[value]]}
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            )
            return True
        except HttpError as e:
            raise Exception(f"Ошибка записи значения: {e}")
    
    async def write_range(
        self,
        sheet_name: str,
        range_a1: str,
        values: List[List[Any]]
    ) -> bool:
        """Запись значений в диапазон"""
        try:
            range_name = f"{sheet_name}!{range_a1}"
            
            body = {'values': values}
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            )
            return True
        except HttpError as e:
            raise Exception(f"Ошибка записи диапазона: {e}")
    
    async def clear_cell(
        self,
        sheet_name: str,
        cell: str
    ) -> bool:
        """Очистка ячейки"""
        try:
            range_name = f"{sheet_name}!{cell}"
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    body={}
                ).execute()
            )
            return True
        except HttpError as e:
            raise Exception(f"Ошибка очистки ячейки: {e}")
    
    async def clear_range(
        self,
        sheet_name: str,
        range_a1: str
    ) -> bool:
        """Очистка диапазона"""
        try:
            range_name = f"{sheet_name}!{range_a1}"
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    body={}
                ).execute()
            )
            return True
        except HttpError as e:
            raise Exception(f"Ошибка очистки диапазона: {e}")
    
    async def get_sheets_info(self) -> List[Dict[str, Any]]:
        """Получение информации о листах"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.service.spreadsheets().get(
                    spreadsheetId=self.spreadsheet_id
                ).execute()
            )
            
            sheets = []
            for sheet in result.get('sheets', []):
                props = sheet.get('properties', {})
                grid_props = props.get('gridProperties', {})
                sheets.append({
                    'title': props.get('title'),
                    'id': props.get('sheetId'),
                    'rows': grid_props.get('rowCount', 1000),
                    'columns': grid_props.get('columnCount', 26)
                })
            
            return sheets
        except HttpError as e:
            raise Exception(f"Ошибка получения информации о листах: {e}")


# Синглтон экземпляр
google_sheets_service = GoogleSheetsService()