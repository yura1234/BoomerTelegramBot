import os
import pytz
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import functions
from aiogram.filters.command import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardButton, CallbackQuery,\
                        input_media_photo, input_media_video
from aiogram import Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import *

from loader import config, client, bot
from bot.models.database import User, BroadcastData, BroadcastDataHistory
from bot.models.callback import BroadcastMenuCallback, BroadcastBtnCallback
from bot.models.state import BroadcastState
from bot.handlers.user import show_message


router = Router()
logger = logging.getLogger(__name__)


async def check_if_user_admin(user_id: int) -> bool:
    find_admin_user = await client(functions.users.GetFullUserRequest(
        id=list(config["Admin"].values())[0]
    ))
    return find_admin_user.full_user.id == user_id


@router.message(Command("getusers"))
async def get_users_file(message: Message) -> None:
    if await check_if_user_admin(message.from_user.id):
        all_users = await User.all()
        len_users = len(all_users)
        file_name = f"{len_users}_users_{datetime.now().strftime("%d_%m_%Y-%H_%M_%S")}.txt"

        await message.answer(
            f"В базе данных было найдено {len_users} пользователей формирую файл."
        )

        with open(file=file_name, mode="w", encoding="utf-8") as f:
            for user in all_users:
                f.write(f"{user.user_id}, {user.username}, {user.fullname}\n")

        await message.answer_document(
            document=FSInputFile(os.path.join(os.getcwd(), file_name))
        )

        os.remove(file_name)
    else:
        await message.answer(
            "Вы не являетесь администратором данного телеграмм бота!"
        )


@router.message(Command("broadcast"))
async def show_broadcast_menu(message: Message) -> None:
    if await check_if_user_admin(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="Создать новость",
                callback_data=BroadcastMenuCallback(
                    broad_type="Create").pack()),
            InlineKeyboardButton(
                text="Показать прошлые новости",
                callback_data=BroadcastMenuCallback(broad_type="Show").pack()),
            width=1
        )

        await message.answer(
            "Выберете команду для создания новости:",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(
            "Вы не являетесь администратором данного телеграмм бота!"
        )


@router.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Create"))
async def create_broadcast_message(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "Выберете сообщение для массовой рассылки пользователям:"
    )
    await state.set_state(BroadcastState.distrib_message)


@router.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Show"))
async def show_broadcast_buttons(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    buttons = []
    current_date = datetime.now(pytz.timezone("Europe/Moscow"))
    broadcast_data = await BroadcastData.all().filter(
        created_date__gt = current_date - timedelta(days=2)
    )
    
    for data in broadcast_data:
        buttons.append(
            InlineKeyboardButton(
                text=f"{data.created_date.strftime("%d/%m/%Y %H:%M")}",
                callback_data=BroadcastBtnCallback(id=data.id).pack())
        )

    builder.row(*buttons, width=2)

    await callback.message.answer(
        "Новости за последние 48 часов",
        reply_markup=builder.as_markup()
    )


@router.callback_query(BroadcastBtnCallback.filter(F.id))
async def show_broadcast_message(
    callback: CallbackQuery,
    callback_data: BroadcastBtnCallback,
) -> None:
    builder = InlineKeyboardBuilder()
    get_message = await BroadcastData.filter(id=callback_data.id).first()

    find_admin_user = await client(functions.users.GetFullUserRequest(
        id=list(config["Admin"].values())[0]
    ))

    await show_message(get_message, find_admin_user.full_user.id)

    builder.row(
        InlineKeyboardButton(
            text="Редактировать",
            callback_data=BroadcastMenuCallback(
                broad_type="Edit",
                id=callback_data.id).pack()
        ),
        InlineKeyboardButton(
            text="Удалить",
            callback_data=BroadcastMenuCallback(
                broad_type="Delete",
                id=callback_data.id).pack()
        ),
        width=2
    )


@router.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Delete"))
async def delete_broadcast_message(
    callback: CallbackQuery,
    callback_data: BroadcastBtnCallback
) -> None:
    picked_message = await BroadcastData.get_or_none(id=callback_data.id)

    if picked_message == None:
        await callback.message.answer(
            "Данная новость была удалена ранее!"
        )
        return

    diff_time = datetime.now(pytz.timezone("Europe/Moscow")) - picked_message.created_date
    if diff_time.days < 2:
        last_history_list = await BroadcastDataHistory.filter(broadcast_data_id=picked_message.id)
        
        for data in last_history_list:
            try:
                await bot.delete_message(
                    chat_id=data.user_id,
                    message_id=data.message_id
                )

                await callback.message.answer(
                    "Новость успешно удалена!"
                )
            except Exception as ex:
                logger.warning(ex)
            await asyncio.sleep(.05)

        await picked_message.delete()
    else:
        await callback.message.answer(
            "Последнее новостное сообщение нельзя удалить так как прошло больше 48 часов."
        )


@router.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Edit"))
async def edit_broadcast(
    callback: CallbackQuery,
    callback_data: BroadcastBtnCallback,
    state: FSMContext
) -> None:
    picked_message = await BroadcastData.filter(id=callback_data.id).first()

    diff_time = datetime.now(pytz.timezone("Europe/Moscow")) - picked_message.created_date
    if diff_time.days < 2:
        await callback.message.answer(
            "Введите сообщение для рекдактирования выбранного:"
        )

        await state.update_data(id=callback_data.id)
        await state.set_state(BroadcastState.edit_message)
    else:
        await callback.message.answer(
            "Последнее новостное сообщение нельзя удалить так как прошло больше 48 часов."
        )


@router.message(BroadcastState.edit_message)
async def edit_broadcast_message(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    message_id = data.get("id")
    await state.clear()

    find_message = await BroadcastData.get_or_none(id=int(message_id))

    if find_message == None:
        await message.answer(
            "Данная новость была удалена ранее!"
        )
        return

    if message.text:
        msg_type = BroadcastData.TypeMessage.TEXT
        text = message.text
        file_id = ""
    elif message.video:
        msg_type = BroadcastData.TypeMessage.VIDEO
        text = message.caption
        file_id = message.video.file_id
    elif message.photo:
        msg_type = BroadcastData.TypeMessage.PHOTO
        text = message.caption
        file_id = message.photo[0].file_id

    if find_message.type != msg_type:
        await message.answer(
            f"Тип предыдущего({find_message.type}) и " +\
            f"текущего({msg_type}) сообщений должен совпадать!"
        )
        return

    find_message.type = msg_type
    find_message.caption_text = text
    find_message.file_id = file_id
    await find_message.save()

    last_history_list = await BroadcastDataHistory.filter(broadcast_data_id=find_message.id)

    for data in last_history_list:
        try:
            if message.text:
                await bot.edit_message_text(
                    text=find_message.caption_text,
                    chat_id=data.user_id,
                    message_id=data.message_id
                )
            elif message.photo:
                await bot.edit_message_media(
                    media=input_media_photo.InputMediaPhoto(
                        media=find_message.file_id,
                        caption=find_message.caption_text
                    ),
                    chat_id=data.user_id,
                    message_id=data.message_id
                )
            elif message.video:
                await bot.edit_message_media(
                    media=input_media_video.InputMediaVideo(
                        media=find_message.file_id,
                        caption=find_message.caption_text
                    ),
                    chat_id=data.user_id,
                    message_id=data.message_id
                )
        except Exception as ex:
            logger.warning(ex)
        await asyncio.sleep(.05)


async def broadcaster(user_id: int, broadcast_data: BroadcastData) -> bool:
    try:
        message = await show_message(broadcast_data, user_id)

        await BroadcastDataHistory.create(
            user_id=message.chat.id,
            message_id=message.message_id,
            broadcast_data_id=broadcast_data.id
        )
    except TelegramRetryAfter as e:
        logger.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.retry_after} seconds.")
        await asyncio.sleep(e.retry_after)
        return await broadcaster(user_id, broadcast_data)
    except TelegramForbiddenError as e:
        logger.error(f"Target [ID:{user_id}]: blocked by user")
    except TelegramNotFound as e:
        logger.error(f"Target [ID:{user_id}]: invalid user ID")
    except TelegramAPIError as e:
        logger.exception(f"Target [ID:{user_id}]: failed")
    else:
        return True

    return False


@router.message(BroadcastState.distrib_message)
async def get_broadcast_message(message: Message, state: FSMContext) -> None:
    await state.clear()

    if message.text:
        msg_type = BroadcastData.TypeMessage.TEXT
        text = message.text
        file_id = ""
    elif message.video:
        msg_type = BroadcastData.TypeMessage.VIDEO
        text = message.caption
        file_id = message.video.file_id
    elif message.photo:
        msg_type = BroadcastData.TypeMessage.PHOTO
        text = message.caption
        file_id = message.photo[0].file_id

    broadcast_data = await BroadcastData.create(
        type=msg_type,
        caption_text=text,
        file_id=file_id
    )

    all_users = await User.all()
    logger.info(f"Start broadcast message for {len(all_users)} users.")
    count = 0
    try:
        for user in all_users:
            if await broadcaster(user.user_id, broadcast_data):
                count += 1
            await asyncio.sleep(.05)
    finally:
        logger.info(f"{count} messages successful sent.")