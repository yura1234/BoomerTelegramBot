from configparser import ConfigParser
from telethon.sync import TelegramClient
from aiogram import Bot, Dispatcher


config = ConfigParser()
config.read("settings.ini", encoding="utf-8")

tortoise_orm_config = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {
        "models": {
            "models": ["bot.models.database", "aerich.models"],
            "default_connection": "default",
        },
    },
    "use_tz": False,
    "timezone": "Europe/Moscow"
}

client = TelegramClient(session=config["General"]["SessionTelethonName"],
                        api_id=int(config["General"]["ApiID"]),
                        api_hash=config["General"]["ApiHash"]
)
bot = Bot(token=config["General"]["Token"])
dp = Dispatcher()
