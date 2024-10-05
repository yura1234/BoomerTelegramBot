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

    approve_user_channels = await AccesChannelUser.filter(
        user_id=update.from_user.id,
        permission=True
    )

    for k,v in channels.items():
        for user_channel in approve_user_channels:
            if v == user_channel.product and channel_links[k].split("/")[-1].startswith(part_link):
                await update.approve()
                logger.info(f"User {update.from_user.id} approved to join channel {user_channel.product}")
                return

    await update.decline()
    logger.info(f"User {update.from_user.id} decline to join channel with part link {part_link}")
