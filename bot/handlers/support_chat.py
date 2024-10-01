import os
import logging
from aiogram import Router
from aiogram.types import User as TgUser
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardButton
from aiogram import F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import functions
from telethon import types as telethonTypes
from telethon.errors.rpcbaseerrors import BadRequestError
from tortoise import timezone

from loader import config, client, bot
from bot.models.callback import ChatTypeCallback
from bot.models.database import SupportChat, LastUserMessage


router = Router()
logger = logging.getLogger(__name__)
support_users = list(config["SupportUsers"].values())
support_chats = config["allPrograms.OnlySupportChats"]
support_chats_type = config["allPrograms.OnlySupportChats.type"]

coding_services_chats = config["allPrograms.CodingServicesChats"]

channel_chats = config["allPrograms.OnlyChannelChats"]
channel_links = config["OnlyChannelLinks"]

order_chats = config["orderParts"]

diag_equip_chats = config["diagEquipment"]
equip_photos = config["diagEquipment.PhotoPath"]

path_photos = os.path.join(os.getcwd(), "photos", "")


def get_user_title(user_data: TgUser) -> str | int:
    if user_data.username:
        return user_data.username
    elif user_data.full_name:
        return user_data.full_name
    else:
        return user_data.id


async def erase_message(user_id: int, message_id: int) -> None:
    last_message = await LastUserMessage.get_or_none(user_id=user_id)

    if last_message is None:
        await LastUserMessage.create(
            user_id=user_id,
            message_id=message_id
        )
    else:
        current_time = timezone.now()
        if (current_time - last_message.updated_date).days < 2:
            await bot.delete_message(
                chat_id=last_message.user_id,
                message_id=last_message.message_id
            )

        last_message.message_id = message_id
        await last_message.save()


@router.message(Command("support"))
async def support_chat(message: Message) -> None:
    msg = "Для получения более подробной информаци " +\
        "или услуге Вы можете отправить сообщение на " +\
        "запрос в чате ниже или на почту support@bimmer-online.ru"

    user = get_user_title(message.from_user)

    chat_name = f"{user} запрос поддержки"

    link = await create_chat(message.from_user.id, chat_name, "support_chat")

    msg = f"По вашему запросу поддержки был создан чат, ссылка на чат {link}"
    await message.answer(
        msg
    )
    logger.info(f"User {message.from_user.id} get chat link - {link}")


@router.callback_query(ChatTypeCallback.filter(F.con_type == "OnlySupportChats"))
async def only_support_chats(callback: CallbackQuery, callback_data: ChatTypeCallback) -> None:
    chat_type = ""
    if callback_data.chat_type == "OrderParts":
        chat = order_chats
    elif callback_data.chat_type == "Support":
        if callback_data.key in support_chats.keys():
            chat = support_chats
            if support_chats_type[callback_data.key] == "поддержка":
                chat_type = "поддержка"
        else:
            chat = coding_services_chats
    elif callback_data.chat_type == "DiagEquip":
        chat = diag_equip_chats
        chat_type = "оборудованию"

        if chat[callback_data.key] != "Написать запрос на оборудование":
            await callback.message.answer_photo(
                FSInputFile(path=path_photos + equip_photos[callback_data.key]),
                caption=diag_equip_chats[callback_data.key]
            )

    if chat_type == "":
        if support_chats_type[callback_data.key] == "продукт":
            chat_type = "продукту"
        else:
            chat_type = "услуге"
    elif chat_type == "поддержка":
        msg = "Для получения более подробной информаци " +\
            "или услуге Вы можете отправить сообщение на " +\
            "запрос в чате ниже или на почту support@bimmer-online.ru"

    msg = f"Для получения более подробной информации по {chat_type} " +\
        f"\"{chat[callback_data.key]}\" Вы можете отправить сообщение на " +\
        "запрос в чате ниже или на почту support@bimmer-online.ru"

    builder = InlineKeyboardBuilder()
    callback_data.con_type = "CreateChat"

    builder.row(
        InlineKeyboardButton(
            text="Создать чат с поддержкой",
            callback_data=callback_data.pack())
        )

    if callback_data.chat_type == "OrderParts" and callback_data.key == "chat3":
        msg = "Уважаемые клиенты, перед отправкой запроса на поиск детали " +\
            "просьба ознакомиться с правилами заказа:\n" +\
            "1) Сроки поставки составляют от 2-х месяцев\n" +\
            "2) Вес одной детали не более 30 кг\n" +\
            "3) Максимальные габаритные размеры упаковки не должны превышать 180x60x60 см"
    elif callback_data.chat_type == "OrderParts" and callback_data.key in ("chat1", "chat2"):
        msg = "Напишите в чат Ваш запрос с указанием артикула детали и VIN номера автомобиля"

    answer_message = await callback.message.answer(
        msg,
        reply_markup=builder.as_markup()
    )
    await erase_message(callback.from_user.id, answer_message.message_id)


async def create_chat(user_id: int, chat_name: str, contract_type: str) -> str:
    get_chat = await SupportChat.get_or_none(
        contract_type=contract_type,
        user_id=user_id
    )

    if get_chat:
        try:
            await client(
                functions.messages.CheckChatInviteRequest(
                    hash=get_chat.link.split("/")[-1][1:]
                )
            )
        except BadRequestError:
            await get_chat.delete()
            logger.info(f"Chat with id {get_chat.chat_id} was deleted! Сreate new chat.")
            get_chat = None

    if get_chat is None:
        user_entity = await client.get_entity(telethonTypes.PeerUser(user_id))
        # user_entity = await client.get_input_entity(telethonTypes.PeerUser(user_id))
        result = await client(
            functions.messages.CreateChatRequest(
            users=[*support_users, user_entity],
            title=chat_name
            )
        )
        chat_id = result.updates.updates[1].participants.chat_id
        chat = await client.get_entity(telethonTypes.PeerChat(chat_id))
        chat_link = await client(
            functions.messages.ExportChatInviteRequest(
                peer=chat
            )
        )

        await SupportChat.create(
            chat_id=chat_id,
            contract_type=contract_type,
            chat_name=chat_name,
            link=chat_link.link,
            user_id=user_id
        )
        return chat_link.link

    return get_chat.link


@router.callback_query(ChatTypeCallback.filter(F.con_type == "CreateChat"))
async def create_support_chats(callback: CallbackQuery, callback_data: ChatTypeCallback) -> None:
    if callback_data.chat_type == "Support":
        if callback_data.key in support_chats.keys():
            chat = support_chats
        else:
            chat = coding_services_chats
    elif callback_data.chat_type == "Channel":
        chat = channel_chats
    elif callback_data.chat_type == "OrderParts":
        chat = order_chats
    else:
        chat = diag_equip_chats

    user = get_user_title(callback.from_user)
    if support_chats_type[callback_data.key] == "поддержка":
        chat_name = f"{user} запрос поддержки"
    elif callback_data.chat_type == "DiagEquip" and callback_data.key == "chat5":
        chat_name = f"{user} запрос на оборудование"
    else:
        chat_name = f"{user} {support_chats_type[callback_data.key]} {chat[callback_data.key]}"

    link = await create_chat(callback.from_user.id, chat_name, chat[callback_data.key])

    if support_chats_type[callback_data.key] == "поддержка":
        msg = f"По вашему запросу поддержки был создан чат, ссылка на чат {link}"
    else:
        msg = f"По вашему запросу {support_chats_type[callback_data.key]} " +\
            f"{chat[callback_data.key]} был создан чат, ссылка на чат {link}"

    answer_message = await callback.message.answer(
        msg
    )
    await erase_message(callback.from_user.id, answer_message.message_id)
    logger.info(f"User {callback.from_user.id} get chat link - {link}")
