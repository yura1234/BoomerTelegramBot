import asyncio
import logging
import re
import os
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
from aiogram.utils.media_group import MediaGroupBuilder

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

support_chats = config["MainInformation.allPrograms.OnlySupportChats"]
support_users = list(config["SupportUsers"].values())

channel_chats = config["MainInformation.allPrograms.OnlyChannelChats"]
channel_links = config["OnlyChannelLinks"]

order_chats = config["MainInformation.orderParts"]

diag_equip_chats = config["MainInformation.diagEquipment"]
equip_photos = config["MainInformation.diagEquipment.PhotoPath"]

path_photos = os.getcwd() + "\\photos\\"

key_chan_list = list(channel_chats.keys())
val_chan_list = list(channel_chats.values())

moderators = config["Moderators"]

all_program_keys = InlineKeyboardBuilder()
order_parts_keys = InlineKeyboardBuilder()
diag_equip_keys = InlineKeyboardBuilder()

equip_dict = dict(diag_equip_chats)
equip_dict.popitem()

inline_keyboards_arr = []

client = TelegramClient(config["General"]["SessionTelethonName"], api_id, api_hash)
client.start()

bot = Bot(token=bot_token)
dp = Dispatcher()


async def set_menu(bot: Bot) -> None:
    main_menu_commands = [
        BotCommand(command="/all_programs", description="Все программы"),
        BotCommand(command="/diag_equipment", description="Диагностическое оборудование"),
        BotCommand(command="/order_parts", description="Заказ запчастей"),
        BotCommand(command="/support", description="Написать запрос в поддержку")
    ]

    await bot.set_my_commands(main_menu_commands)


@dp.message(Command("diag_equipment"))
async def diag_equipment(message: types.Message) -> None:
    group_photos = MediaGroupBuilder()

    for key,val in equip_dict.items():
        # await message.answer_photo(
        #     types.FSInputFile(path=path_photos + equip_photos[key]), caption=val
        # )
        # if key != "chat5":
        group_photos.add(type="photo", media=types.FSInputFile(path=path_photos + equip_photos[key]), caption=val)

    await bot.send_media_group(
        chat_id=message.from_user.id,
        media=group_photos.build()
    )

    await message.answer(
        "Выберете необходимое оборудование для покупки",
        reply_markup=diag_equip_keys.as_markup()
    )


@dp.message(Command("all_programs"))
async def all_programs(message: types.Message) -> None:
    await message.answer(
        "Выберете необходимую программу или услугу",
        reply_markup=all_program_keys.as_markup()
    )


@dp.message(Command("order_parts"))
async def order_parts(message: types.Message) -> None:
    await message.answer(
        "Выберете необходимую программу или услугу",
        reply_markup=order_parts_keys.as_markup()
    )


@dp.message(Command("support"))
async def support_chat(message: types.Message) -> None:
    msg = "Для получения более подробной информаци " +\
        f"или услуге Вы можете отправить сообщение на " +\
        "запрос в чате ниже или на почту support@bimmer-online.com"

    users = support_users.copy()
    users.append(message.from_user.username)

    chat_name = f"{message.from_user.username} запрос поддержки"

    link = await create_chat(users, chat_name, "support_chat")

    msg = f"По вашему запросу поддержки был создан чат, ссылка на чат {link}"
    await message.answer(
        msg
    )
    logging.info(f"User {message.from_user.username} get chat link - {link}")


@dp.callback_query(ChatType.filter(F.con_type == "OnlySupportChats"))
async def only_support_chats(callback: CallbackQuery, callback_data: ChatType) -> None:
    if callback_data.chat_type == "OrderParts":
        chat = order_chats
    elif callback_data.chat_type == "Support":
        chat = support_chats
    elif callback_data.chat_type == "DiagEquip":
        chat = diag_equip_chats

    msg = "Для получения более подробной информаци по продукту " +\
    f"\"{chat[callback_data.key]}\" или услуге Вы можете отправить сообщение на " +\
    "запрос в чате ниже или на почту support@bimmer-online.com"
    builder = InlineKeyboardBuilder()
    callback_data.con_type = "CreateChat"

    builder.row(
        types.InlineKeyboardButton(
            text="Создать чат с поддержкой",
            callback_data=callback_data.pack())
        )
    
    if callback_data.chat_type == "OrderParts" and callback_data.key == "chat3":
        msg = "Уважаемые клиенты, перед отправкой запроса на поиск детали просьба ознакомиться с правилами заказа:" +\
        "1) Сроки поставки составляют от 2-х месяцев" +\
        "2) Вес одной детали не более 30 кг" +\
        "3) Максимальные габаритные размеры упаковки не должны превышать 180x60x60 см"
    elif callback_data.chat_type == "OrderParts" and (callback_data.key == "chat1" or callback_data.key == "chat2"):
        msg = "Напишите в чат Ваш запрос с указанием артикула детали и VIN номера автомобиля"

    
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
    elif callback_data.chat_type == "Channel":
        chat = channel_chats
    elif callback_data.chat_type == "OrderParts":
        chat = order_chats
    else:
        chat = diag_equip_chats

    users = support_users.copy()
    users.append(callback.from_user.username)

    chat_name = f"{callback.from_user.username} продукт {chat[callback_data.key]}"

    if callback_data.chat_type == "DiagEquip" and callback_data.key == "chat5":
        chat_name = f"{callback.from_user.username} запрос на оборудование"

    link = await create_chat(users, chat_name, chat[callback_data.key])

    msg = f"По вашему запросу продукта {chat[callback_data.key]} был создан чат, ссылка на чат {link}"
    await callback.message.answer(
        msg
    )
    logging.info(f"User {callback.from_user.username} get chat link - {link}")


@dp.callback_query(ChatType.filter(F.con_type == "OnlyChannelChats"))
async def only_channel_chats(callback: CallbackQuery, callback_data: ChatType, state: FSMContext) -> None:
    msg = f"Для доступа в канал {channel_chats[callback_data.key]} необходимо указать Ваш рабочий email и название СТО.\n" +\
        "Либо направьте запрос в поддержку."
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
        "Укажите Ваш email:"
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

    await message.answer("Укажите название Вашей СТО:")
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

    position = val_chan_list.index(product)

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Предоставить ссылку",
            callback_data=AccesData(user_id=message.from_user.id, product=key_chan_list[position], permission=True).pack()),
        types.InlineKeyboardButton(
            text="НЕ предоставлять ссылку",
            callback_data=AccesData(user_id=message.from_user.id, product=key_chan_list[position], permission=False).pack()),
        )
    
    await message.answer("Ожидайте ответа модератора.") 

    await bot.send_message(
        chat_id=moderator_id,
        text=msg,
        reply_markup=builder.as_markup()
        )


@dp.callback_query(AccesData.filter(F.permission == True))
async def grant_permission(callback: CallbackQuery, callback_data: AccesData) -> None:
    msg = f"Ссылка для подключения к чату по программе {channel_chats[callback_data.product]}\n" +\
        f"{channel_links[callback_data.product]}"
    
    await callback.message.answer("Принят")

    await bot.send_message(
        chat_id=callback_data.user_id,
        text=msg
        )


@dp.callback_query(AccesData.filter(F.permission == False))
async def decline_permission(callback: CallbackQuery, callback_data: AccesData) -> None:
    msg = f"Ваш запрос для подключения к чату по программе {channel_chats[callback_data.product]} отклонен!"
    
    await callback.message.answer("Отклонен")

    await bot.send_message(
        chat_id=callback_data.user_id,
        text=msg
        )


def add_button_keys(
        builder: InlineKeyboardBuilder,
        chats: dict[str, str],
        callback_type: str, 
        chat_type: str, 
        max_len: int, 
        width: int
) -> None:
    chat_keys = list(chats.keys())
    keys_arr = []

    i = 0
    w = 0
    while i < len(chat_keys):
        if len(chats[chat_keys[i]]) < max_len and w < width:
            keys_arr.append(
                types.InlineKeyboardButton(
                text=chats[chat_keys[i]],
                callback_data=ChatType(
                    key=chat_keys[i], 
                    con_type=callback_type,
                    chat_type=chat_type).pack()
                )
            )
            w += 1
            i += 1
        elif len(chats[chat_keys[i]]) >= max_len:
            if len(keys_arr) > 0:
                builder.row(*keys_arr, width=width)
                keys_arr = []

            keys_arr.append(
                types.InlineKeyboardButton(
                text=chats[chat_keys[i]],
                callback_data=ChatType(
                    key=chat_keys[i], 
                    con_type=callback_type,
                    chat_type=chat_type).pack()
                )
            )
            i += 1
            w = width
        
        if w == width:
            builder.row(*keys_arr, width=width)
            w = 0
            keys_arr = []


async def main() -> None:
    add_button_keys(all_program_keys, channel_chats, "OnlyChannelChats", "Channel", 20, 3)
    add_button_keys(all_program_keys, support_chats, "OnlySupportChats", "Support", 15, 2)
    add_button_keys(order_parts_keys, order_chats, "OnlySupportChats", "OrderParts", 15, 2)
    add_button_keys(diag_equip_keys, diag_equip_chats, "OnlySupportChats", "DiagEquip", 15, 2)

    dp.startup.register(set_menu)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
