from pydantic_settings import BaseSettings, SettingsConfigDict

class GoogleSettings(BaseSettings):
    spreadsheet_id: str
    sheet_name: str = "Лист1" # Имя листа по умолчанию
    service_account_file: str 
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class BotSettings(BaseSettings):
    bot_token: str
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class AppSettings(BaseSettings):
    lock_timeout: int = 10 # Таймаут блокировки в секундах

settings = AppSettings()
google_settings = GoogleSettings()
bot_settings = BotSettings()