from aiogram import Bot
from aiogram.client.default import DefaultBotProperties 
from config.settings import bot_settings

def create_bot() -> Bot:
    return Bot(token=bot_settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))