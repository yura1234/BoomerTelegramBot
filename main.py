import asyncio
import logging
import re
from database import *

from configparser import ConfigParser
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import BotCommand, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from telethon.sync import TelegramClient
from telethon import functions
from telethon import types as telethonTypes
# from telethon.errors import PeerIdInvalidError
from telethon.errors.rpcbaseerrors import BadRequestError

import nest_asyncio
nest_asyncio.apply()


class ChatType(CallbackData, prefix="con"):
    key: str
    con_type: str
    chat_type: str


class AccesData(CallbackData, prefix="acc"):
    user_id: int
    product: str
    permission: bool


class UserData(StatesGroup):
    username = State()
    product = State()
    email = State()
    sto_name = State()


log_file_format = f"log-{datetime.now().strftime("%d_%m_%Y-%H_%M_%S")}.log"
logging.basicConfig(level=logging.INFO, filename=log_file_format, filemode="w", 
                    encoding='utf-8', format="%(asctime)s %(levelname)s %(message)s")

config = ConfigParser()
config.read("settings.ini", encoding="utf-8")

db = DataBase("database")
loop = asyncio.get_event_loop()
loop.run_until_complete(db.create_connection())

bot_token = config["General"]["Token"]
api_id = int(config["General"]["ApiID"])
api_hash = config["General"]["ApiHash"]

support_chats = config["OnlySupportChats"]
support_users = list(config["SupportUsers"].values())

channel_chats = config["OnlyChannelChats"]
channel_links = config["OnlyChannelLinks"]

moderators = config["Moderators"]

all_program_keys = InlineKeyboardBuilder()

client = TelegramClient(config["General"]["alphaBoomer001"], api_id, api_hash)
client.start()

bot = Bot(token=bot_token)
dp = Dispatcher()


async def set_menu(bot: Bot) -> None:
    main_menu_commands = [
        BotCommand(command="/all_programs", description="Все программы"),
        BotCommand(command="/support", description="Написать запрос в поддержку")
    ]

    await bot.set_my_commands(main_menu_commands)


@dp.message(Command("all_programs"))
async def all_programs(message: types.Message) -> None:
    msg = "Доступные услуги по направлениям BMW / Mini / Motorrad / Rolls-Royce"

    await message.answer(
        msg,
        reply_markup=all_program_keys.as_markup()
    )


@dp.message(Command("support"))
async def diag_equip_prog(message: types.Message) -> None:
    msg = "Для получения более подробной информаци " +\
        f"или услуге Вы можете отправить сообщение на " +\
        "запрос в чате ниже или на почту support@bimmer-online.com"

    users = support_users.copy()
    users.append(message.from_user.username)

    chat_name = f"{message.from_user.username} запрос поддержки"

    link = await create_chat(users, chat_name, "diag_equip")

    msg = f"По вашему запросу поддержки был создан чат, ссылка на чат {link}"
    await message.answer(
        msg
    )
    logging.info(f"User {message.from_user.username} get chat link - {link}")


# @dp.callback_query(F.data == "OnlySupportChats")
@dp.callback_query(ChatType.filter(F.con_type == "OnlySupportChats"))
async def only_support_chats(callback: CallbackQuery, callback_data: ChatType) -> None:
    msg = "Для получения более подробной информаци по продукту " +\
    f"\"{support_chats[callback_data.key]}\" или услуге Вы можете отправить сообщение на " +\
    "запрос в чате ниже или на почту support@bimmer-online.com"
    builder = InlineKeyboardBuilder()
    callback_data.con_type = "CreateChat"

    builder.row(
        types.InlineKeyboardButton(
            text="Создать чат с поддержкой",
            callback_data=callback_data.pack())
        )

    await callback.message.answer(
        msg,
        reply_markup=builder.as_markup()
    )


async def create_chat(users: list, chat_name: str, contract_type: str) -> str:
    chat_row_from_db = await db.get_chat_link("created_chats", contract_type, users[-1])

    if chat_row_from_db != None:
        try:
            await client(functions.messages.CheckChatInviteRequest(hash=chat_row_from_db[4].split("/")[-1][1:]))
        except BadRequestError:
            await db.delete_chat_link("created_chats", chat_row_from_db[0])
            logging.info(f"Chat with id {chat_row_from_db[0]} was deleted! Сreate new chat.")
            chat_row_from_db = None
    
    if chat_row_from_db == None:
        result = await client(functions.messages.CreateChatRequest(
            users=users,
            title=chat_name
            ))
        
        chat_id = result.updates.updates[1].participants.chat_id

        chat = await client.get_entity(telethonTypes.PeerChat(chat_id))   
        chat_link = await client(functions.messages.ExportChatInviteRequest(
                peer=chat
            ))

        contract = ContractChat(
            id=chat_id,
            contract_type=contract_type,
            chat_name=chat_name,
            users_in_chat=','.join(users),
            link=chat_link.link
            )
        
        await db.insert("created_chats", contract.model_dump())
        return chat_link.link
    
    return chat_row_from_db[4]


@dp.callback_query(ChatType.filter(F.con_type == "CreateChat"))
async def create_support_chats(callback: CallbackQuery, callback_data: ChatType) -> None:
    if callback_data.chat_type == "Support":
        chat = support_chats
    else:
        chat = channel_chats

    users = support_users.copy()
    users.append(callback.from_user.username)

    chat_name = f"{callback.from_user.username} продукт {chat[callback_data.key]}"

    link = await create_chat(users, chat_name, chat[callback_data.key])

    msg = f"По вашему запросу продукта {chat[callback_data.key]} был создан чат, ссылка на чат {link}"
    await callback.message.answer(
        msg
    )
    logging.info(f"User {callback.from_user.username} get chat link - {link}")


@dp.callback_query(ChatType.filter(F.con_type == "OnlyChannelChats"))
async def only_channel_chats(callback: CallbackQuery, callback_data: ChatType, state: FSMContext) -> None:
    msg = f"Для доступа в канал {channel_chats[callback_data.key]} необходимо указать email/название СТО\n" +\
        "или можете написать запрос в поддержку."
    callback_data.con_type = "CreateChat"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Написать запрос",
            callback_data=callback_data.pack())
    )

    await callback.message.answer(
        msg,
        reply_markup=builder.as_markup()
    )

    await callback.message.answer(
        "Сначала укажите email"
    )

    await state.update_data(username=callback.from_user.username)
    await state.update_data(product=channel_chats[callback_data.key])

    await state.set_state(UserData.email)


@dp.message(UserData.email)
async def save_email(message: types.Message, state: FSMContext) -> None:
    email_valid_pattern = r"^\S+@\S+\.\S+$"

    if re.match(email_valid_pattern, message.text) == None:
        await message.answer("Пожалуйста введите корректный емайл адрес")
        return
    
    await state.update_data(email=message.text)

    await message.answer("Пожалуйста введите адрес СТО")
    await state.set_state(UserData.sto_name)


@dp.message(UserData.sto_name)
async def save_sto(message: types.Message, state: FSMContext) -> None:
    if message.text.isspace():
        await message.answer("Пожалуйста введите корректный адрес СТО")
        return
    
    await state.update_data(sto_name=message.text)

    data = await state.get_data()
    username = data.get("username")
    product = data.get("product")
    email = data.get("email")
    sto_name = data.get("sto_name")
    await state.clear()

    msg = f"Пользователь {username} запрашивает доступ к каналу " +\
        f"{product} по указанным данным (emal\название СТО)\n" +\
        f"{email}\n{sto_name}"

    find_user = await client(functions.users.GetFullUserRequest(
        id=list(moderators.values())[0]
    ))
    moderator_id = find_user.full_user.id

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Предоставить ссылку",
            callback_data=AccesData(user_id=message.from_user.id, product=product, permission=True).pack()),
        types.InlineKeyboardButton(
            text="НЕ предоставлять ссылку",
            callback_data=AccesData(user_id=message.from_user.id, product=product, permission=False).pack()),
        )
    
    await message.answer("Ожидайте ответа модератора.") 

    await bot.send_message(
        chat_id=moderator_id,
        text=msg,
        reply_markup=builder.as_markup()
        )


@dp.callback_query(AccesData.filter(F.permission == True))
async def grant_permission(callback: CallbackQuery, callback_data: AccesData) -> None:
    msg = f"Ссылка для подключения к чату по программе {callback_data.product}\n" +\
        f"{channel_links[callback_data.product]}"
    
    await callback.message.answer("Принят")

    await bot.send_message(
        chat_id=callback_data.user_id,
        text=msg
        )


@dp.callback_query(AccesData.filter(F.permission == False))
async def decline_permission(callback: CallbackQuery, callback_data: AccesData) -> None:
    msg = f"Ваш запрос для подключения к чату по программе {callback_data.product}\n отклонен!"
    
    await callback.message.answer("Отклонен")

    await bot.send_message(
        chat_id=callback_data.user_id,
        text=msg
        )


def add_button_keys(add_chats: dict[str, str], callback_type: str, chat_type: str, max_len: int) -> None:
    sup_keys = list(add_chats.keys())

    i = 0
    while i < len(sup_keys):
        if len(add_chats[sup_keys[i]]) <= max_len and len(add_chats[sup_keys[i + 1]]) <= max_len:
            all_program_keys.row(
            types.InlineKeyboardButton(
                text=add_chats[sup_keys[i]],
                callback_data=ChatType(
                    key=sup_keys[i], 
                    con_type=callback_type,
                    chat_type=chat_type).pack()
                ),
            types.InlineKeyboardButton(
                text=add_chats[sup_keys[i + 1]],
                callback_data=ChatType(
                    key=sup_keys[i + 1], 
                    con_type=callback_type,
                    chat_type=chat_type).pack()
                )
            )
            i += 2
        else:
            all_program_keys.row(
            types.InlineKeyboardButton(
                text=add_chats[sup_keys[i]],
                callback_data=ChatType(key=sup_keys[i], 
                                       con_type=callback_type,
                                       chat_type=chat_type).pack()
                )
            )
            i += 1


async def main() -> None:
    add_button_keys(channel_chats, "OnlyChannelChats", "Channel", 20)
    add_button_keys(support_chats, "OnlySupportChats", "Support", 20)

    dp.startup.register(set_menu)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
