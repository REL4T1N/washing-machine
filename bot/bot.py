from aiogram import Bot
from aiogram.client.default import DefaultBotProperties 
from config.settings import bot_settings

def create_bot() -> Bot:
    """
    Создает и настраивает экземпляр Bot.
    
    Returns:
        Bot: Настроенный объект бота с поддержкой HTML.
    """
    return Bot(
        token=bot_settings.bot_token, 
        default=DefaultBotProperties(parse_mode="HTML")
    )