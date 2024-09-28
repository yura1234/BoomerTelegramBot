import logging
from aiogram import Router
from aiogram.types import ChatJoinRequest

from bot.models.database import AccesChannelUser
from loader import config


router = Router()
logger = logging.getLogger(__name__)

channel_names = list(config["allPrograms.OnlyChannelChats"].values())


@router.chat_join_request()
async def check_join_request(update: ChatJoinRequest) -> None:
    full_channel_name = update.chat.full_name.title().lower()
    channel = [c for c in channel_names if c.lower() in full_channel_name][0]

    get_access_channels = await AccesChannelUser.get_or_none(
        user_id=update.from_user.id,
        product=channel
    )

    if get_access_channels != None:
        if get_access_channels.permission:
            await update.approve()
            logger.info(f"User {update.from_user.id} approved to join channel {channel}")
        else:
            await update.decline()
            logger.info(f"User {update.from_user.id} decline to join channel {channel}")
    else:
        await update.decline()
        logger.warning(f"User {update.from_user.id} with channel {channel} not found in DB")