from pydantic import computed_field, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from config.constants import GOOGLE_SHEETS_BASE_URL


class GoogleSettings(BaseSettings):
    """Настройки интеграции с Google Sheets API."""
    spreadsheet_id: str = Field(description="ID Google таблицы из URL")
    sheet_name: str = Field(default="Лист1", description="Название рабочего листа")
    service_account_file: str = Field(description="Путь к JSON файлу сервисного аккаунта")

    @computed_field
    @property
    def full_url(self) -> str:
        """Возвращает полную ссылку на таблицу."""
        return f"{GOOGLE_SHEETS_BASE_URL}{self.spreadsheet_id}"
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


class BotSettings(BaseSettings):
    """Настройки Telegram бота."""
    bot_token: str = Field(description="Токен бота от @BotFather")
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


class AppSettings(BaseSettings):
    """Общие настройки приложения."""
    lock_timeout: int = Field(default=10, description="Таймаут блокировки ресурса в секундах")


settings = AppSettings()
google_settings = GoogleSettings()
bot_settings = BotSettings()