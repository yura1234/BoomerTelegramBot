# import logging
# import os
# from datetime import datetime
from configparser import ConfigParser
from telethon.sync import TelegramClient
from aiogram import Bot, Dispatcher


# logging.basicConfig(level=logging.INFO, 
#                     filename=f"log-{datetime.now().strftime("%d_%m_%Y-%H_%M_%S")}.log", 
#                     filemode="w", 
#                     encoding='utf-8', 
#                     format="%(asctime)s %(levelname)s %(message)s"
# )
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

# support_chats = config["allPrograms.OnlySupportChats"]
# support_chats_type = config["allPrograms.OnlySupportChats.type"]
# support_users = list(config["SupportUsers"].values())

# coding_services_chats = config["allPrograms.CodingServicesChats"]

# channel_chats = config["allPrograms.OnlyChannelChats"]
# channel_links = config["OnlyChannelLinks"]

# order_chats = config["orderParts"]

# diag_equip_chats = config["diagEquipment"]
# equip_photos = config["diagEquipment.PhotoPath"]

# path_photos = os.path.join(os.getcwd(), "photos", "")

# key_chan_list = list(channel_chats.keys())
# val_chan_list = list(channel_chats.values())

# moderators = config["Moderators"]

# admin = config["Admin"]
