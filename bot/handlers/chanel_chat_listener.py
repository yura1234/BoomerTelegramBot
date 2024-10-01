import logging
from aiogram import Router
from aiogram.types import ChatJoinRequest

from bot.models.database import AccesChannelUser
from loader import config


router = Router()
logger = logging.getLogger(__name__)
channels = config["allPrograms.OnlyChannelChats"]
channel_links = config["OnlyChannelLinks"]


@router.chat_join_request()
async def check_join_request(update: ChatJoinRequest) -> None:
    link = update.invite_link.invite_link.split("/")[-1]
    part_link = link[:link.index(".")]

    for k,v in channel_links.items():
        if part_link in v:
            channel_type = channels[k]
            break

    get_access_channels = await AccesChannelUser.get_or_none(
        user_id=update.from_user.id,
        product=channel_type
    )

    if get_access_channels:
        if get_access_channels.permission:
            await update.approve()
            logger.info(f"User {update.from_user.id} approved to join channel {channel_type}")
        else:
            await update.decline()
            logger.info(f"User {update.from_user.id} decline to join channel {channel_type}")
    else:
        await update.decline()
        logger.warning(f"User {update.from_user.id} with channel {channel_type} not found in DB")
