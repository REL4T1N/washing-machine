from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.constants import GOOGLE_SHEETS_BASE_URL

class GoogleSettings(BaseSettings):
    spreadsheet_id: str
    sheet_name: str = "Лист1" # Имя листа по умолчанию
    service_account_file: str 

    @computed_field
    @property
    def full_url(self) -> str:
        return f"{GOOGLE_SHEETS_BASE_URL}{self.spreadsheet_id}"
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class BotSettings(BaseSettings):
    bot_token: str
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class AppSettings(BaseSettings):
    lock_timeout: int = 10 # Таймаут блокировки в секундах

settings = AppSettings()
google_settings = GoogleSettings()
bot_settings = BotSettings()