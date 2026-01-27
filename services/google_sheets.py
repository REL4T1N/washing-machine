import asyncio
import logging
from typing import List, Optional, Any, Dict

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.constants import SCOPES

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Сервис для работы с Google Sheets API"""
    
    def __init__(self, spreadsheet_id: str, credentials_path: str):
        self.spreadsheet_id = spreadsheet_id
        try:
            logger.info(f"Загрузка файла сервисного аккаунта: {credentials_path}")
            creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("✅ Google Sheets API успешно инициализирован.")
        except FileNotFoundError:
            logger.critical(f"❌ Файл сервисного аккаунта не найден: {credentials_path}")
            raise
        except Exception as e:
            logger.critical(f"❌ Критическая ошибка инициализации Google Sheets: {e}")
            raise

    async def _execute_request(self, func) -> Any:
        """Выполняет блокирующий запрос API в отдельном потоке."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)

    async def get_data(self, sheet_name: str, range_a1: Optional[str] = None) -> List[List[Any]]:
        """Получение данных из таблицы."""
        try:
            range_name = f"{sheet_name}!{range_a1}" if range_a1 else sheet_name
            
            request = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            )
            result = await self._execute_request(request.execute)
            
            return result.get('values', [])
        except HttpError as e:
            logger.error(f"Ошибка чтения данных из '{sheet_name}': {e}")
            raise
    
    async def write_value(self, sheet_name: str, cell: str, value: Any) -> bool:
        """Запись значения в одну ячейку."""
        try:
            range_name = f"{sheet_name}!{cell}"
            body = {'values': [[value]]}
            
            request = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            )
            await self._execute_request(request.execute)
            return True
        except HttpError as e:
            logger.error(f"Ошибка записи значения в '{range_name}': {e}")
            return False
    
    async def clear_cell(self, sheet_name: str, cell: str) -> bool:
        """Очистка ячейки (запись пустой строки)."""
        return await self.write_value(sheet_name, cell, "")

    async def batch_update_values(self, sheet_name: str, updates: List[Dict[str, Any]]) -> bool:
        """
        Массовое обновление значений в РАЗНЫХ ячейках за один запрос.
        Args: updates - список словарей вида:
        [
            {'range': 'B2', 'values': [['Имя 19.01']]},
            {'range': 'D5', 'values': [['Имя 20.01']]}
        ]
        """
        try:
            data = [
                {
                    'range': f"{sheet_name}!{upd['range']}",
                    'values': upd['values']
                }
                for upd in updates
            ]
            body = {'valueInputOption': 'RAW', 'data': data}

            request = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            )
            await self._execute_request(request.execute)
            return True
        except HttpError as e:
            logger.error(f"Ошибка массового обновления в '{sheet_name}': {e}")
            return False
