import asyncio
import logging
from aiogram import Router
from aiogram.filters.command import Command
from aiogram.types import Message
from tortoise.exceptions import IntegrityError

from loader import bot
from bot.models.database import User, BroadcastData


router = Router()
logger = logging.getLogger(__name__)


async def show_message(data: BroadcastData, user_id: int) -> Message | None:
    if data.type == BroadcastData.TypeMessage.TEXT:
        return await bot.send_message(
            chat_id=user_id,
            text=data.caption_text
        )
    elif data.type == BroadcastData.TypeMessage.VIDEO:
        return await bot.send_video(
            chat_id=user_id,
            video=data.file_id,
            caption=data.caption_text
        )
    elif data.type == BroadcastData.TypeMessage.PHOTO:
        return await bot.send_photo(
            chat_id=user_id,
            photo=data.file_id,
            caption=data.caption_text
        )
    else:
        return None


@router.message(Command("start"))
async def start_bot(message: Message) -> None:
    try:
        user_name = ""
        if message.from_user.username is not None:
            user_name = message.from_user.username

        await User.create(
            user_id=message.from_user.id,
            username=user_name,
            fullname=message.from_user.full_name,
        )

        await message.answer(
            "Добро пожаловать в бот поддержки\n" +\
            "Для выбора интересующего раздела нажмите кнопку «Меню»"
        )
    except IntegrityError:
        logger.info(f"User {message.from_user.id} already exist in database.")


@router.message(Command("show_last_news"))
async def show_last_news(message: Message) -> None:
    get_last_news = await BroadcastData.all().order_by("-id").limit(5)

    await message.answer(
        "Список последних новостей за месяц:"
    )

    for news in get_last_news:
        await show_message(news, message.from_user.id)
        await asyncio.sleep(.05)
