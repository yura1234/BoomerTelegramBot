import asyncio
import logging
import re
import os
from datetime import datetime, timedelta
import pytz

from configparser import ConfigParser

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import BotCommand, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import *

from telethon.sync import TelegramClient
from telethon import functions
from telethon import types as telethonTypes
from telethon.errors.rpcbaseerrors import BadRequestError

from aiogram.types import User as TgUser

from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from database_models import *

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


class BroadcastMenuCallback(CallbackData, prefix="brd"):
    broad_type: str
    id: int = -1


class BroadcastBtnCallback(CallbackData, prefix="brdbtn"):
    id: int


class UserData(StatesGroup):
    product = State()
    email = State()
    sto_name = State()


class BroadcastState(StatesGroup):
    distrib_message = State()
    edit_message = State()


log_file_format = f"log-{datetime.now().strftime("%d_%m_%Y-%H_%M_%S")}.log"
logging.basicConfig(level=logging.INFO, filename=log_file_format, filemode="w", 
                    encoding='utf-8', format="%(asctime)s %(levelname)s %(message)s")

config = ConfigParser()
config.read("settings.ini", encoding="utf-8")

tortoise_orm_config = {
    "connections": {"default": "sqlite://db.sqlite3"},
    "apps": {
        "models": {
            "models": ["database_models", "aerich.models"],
            "default_connection": "default",
        },
    },
    "use_tz": False,
    "timezone": "Europe/Moscow"
}

bot_token = config["General"]["Token"]
api_id = int(config["General"]["ApiID"])
api_hash = config["General"]["ApiHash"]

support_chats = config["allPrograms.OnlySupportChats"]
support_chats_type = config["allPrograms.OnlySupportChats.type"]
support_users = list(config["SupportUsers"].values())

coding_services_chats = config["allPrograms.CodingServicesChats"]

channel_chats = config["allPrograms.OnlyChannelChats"]
channel_links = config["OnlyChannelLinks"]

order_chats = config["orderParts"]

diag_equip_chats = config["diagEquipment"]
equip_photos = config["diagEquipment.PhotoPath"]

path_photos = os.path.join(os.getcwd(), "photos", "")

key_chan_list = list(channel_chats.keys())
val_chan_list = list(channel_chats.values())

moderators = config["Moderators"]

admin = config["Admin"]

all_program_keys = InlineKeyboardBuilder()
coding_services_keys = InlineKeyboardBuilder()
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
        BotCommand(command="/coding_services", description="Услуги по кодированию"),
        BotCommand(command="/diag_equipment", description="Диагностическое оборудование"),
        BotCommand(command="/order_parts", description="Заказ запчастей"),
        BotCommand(command="/show_last_news", description="Последние новости за месяц"),
        BotCommand(command="/support", description="Написать запрос в поддержку")
    ]

    await bot.set_my_commands(main_menu_commands)


@dp.message(Command("diag_equipment"))
async def diag_equipment(message: types.Message) -> None:
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


@dp.message(Command("coding_services"))
async def all_programs(message: types.Message) -> None:
    await message.answer(
        "Выберете необходимую программу или услугу",
        reply_markup=coding_services_keys.as_markup()
    )


@dp.message(Command("order_parts"))
async def order_parts(message: types.Message) -> None:
    await message.answer(
        "Выберете необходимую программу или услугу",
        reply_markup=order_parts_keys.as_markup()
    )


@dp.message(Command("show_last_news"))
async def show_last_news(message: types.Message) -> None:
    get_last_news = await BroadcastData.all().order_by("-id").limit(5)

    await message.answer(
        "Список последних новостей за месяц:"
    )

    for news in get_last_news:
        await show_message(news, message.from_user.id)
        await asyncio.sleep(.05)


@dp.message(Command("start"))
async def start_bot(message: types.Message) -> None:
    try:
        user_name = ""
        if message.from_user.username != None:
            user_name = message.from_user.username

        await User.create(
            user_id=message.from_user.id,
            username=user_name,
            fullname=message.from_user.full_name,
        )

        await message.answer(
            "Добро пожаловать в бот поддержки\nДля выбора интересующего раздела нажмите кнопку «Меню»"
        )
    except IntegrityError:
        logging.info(f"User {message.from_user.id} already exist in database.")


async def check_if_user_admin(user_id: int) -> bool:
    find_admin_user = await client(functions.users.GetFullUserRequest(
        id=list(admin.values())[0]
    ))
    return find_admin_user.full_user.id == user_id


async def show_message(data: BroadcastData, user_id: int) -> types.Message:
    if data.type == BroadcastData.TypeMessage.TEXT:
        return await bot.send_message(chat_id=user_id,
                                text=data.caption_text
        )
    elif data.type == BroadcastData.TypeMessage.VIDEO:
        return await bot.send_video(chat_id=user_id,
                                video=data.file_id,
                                caption=data.caption_text
        )
    elif data.type == BroadcastData.TypeMessage.PHOTO:
        return await bot.send_photo(chat_id=user_id,
                                photo=data.file_id,
                                caption=data.caption_text
        )


@dp.message(Command("getusers"))
async def get_users_file(message: types.Message) -> None:
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
            document=types.FSInputFile(os.path.join(os.getcwd(), file_name))
        )

        os.remove(file_name)


@dp.message(Command("broadcast"))
async def show_broadcast_menu(message: types.Message) -> None:
    if await check_if_user_admin(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="Создать новость",
                callback_data=BroadcastMenuCallback(
                    broad_type="Create").pack()),
            types.InlineKeyboardButton(
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


@dp.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Create"))
async def create_broadcast_message(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(
        "Выберете сообщение для массовой рассылки пользователям:"
    )
    await state.set_state(BroadcastState.distrib_message)


@dp.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Show"))
async def show_broadcast_buttons(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    buttons = []
    current_date = datetime.now(pytz.timezone("Europe/Moscow"))
    broadcast_data = await BroadcastData.all().filter(
        created_date__gt = current_date - timedelta(days=2)
    )
    
    for data in broadcast_data:
        buttons.append(
            types.InlineKeyboardButton(
                text=f"{data.created_date.strftime("%d/%m/%Y %H:%M")}",
                callback_data=BroadcastBtnCallback(id=data.id).pack())
        )

    builder.row(*buttons, width=2)

    await callback.message.answer(
        "Новости за последние 48 часов",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(BroadcastBtnCallback.filter(F.id))
async def show_broadcast_message(
    callback: CallbackQuery,
    callback_data: BroadcastBtnCallback,
) -> None:
    builder = InlineKeyboardBuilder()
    get_message = await BroadcastData.filter(id=callback_data.id).first()

    find_admin_user = await client(functions.users.GetFullUserRequest(
        id=list(admin.values())[0]
    ))

    await show_message(get_message, find_admin_user.full_user.id)

    builder.row(
        types.InlineKeyboardButton(
            text="Редактировать",
            callback_data=BroadcastMenuCallback(
                broad_type="Edit",
                id=callback_data.id).pack()
        ),
        types.InlineKeyboardButton(
            text="Удалить",
            callback_data=BroadcastMenuCallback(
                broad_type="Delete",
                id=callback_data.id).pack()
        ),
        width=2
    )

    await callback.message.answer(
        "Выбранное новостное сообщение:",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Delete"))
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
                logging.warning(ex)
            await asyncio.sleep(.05)

        await picked_message.delete()
    else:
        await callback.message.answer(
            "Последнее новостное сообщение нельзя удалить так как прошло больше 48 часов."
        )


@dp.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Edit"))
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


@dp.message(BroadcastState.edit_message)
async def edit_broadcast_message(message: types.Message, state: FSMContext) -> None:
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
                    media=types.input_media_photo.InputMediaPhoto(
                        media=find_message.file_id,
                        caption=find_message.caption_text
                    ),
                    chat_id=data.user_id,
                    message_id=data.message_id
                )
            elif message.video:
                await bot.edit_message_media(
                    media=types.input_media_video.InputMediaVideo(
                        media=find_message.file_id,
                        caption=find_message.caption_text
                    ),
                    chat_id=data.user_id,
                    message_id=data.message_id
                )
        except Exception as ex:
            logging.warning(ex)
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
        logging.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.retry_after} seconds.")
        await asyncio.sleep(e.retry_after)
        return await broadcaster(user_id, broadcast_data)
    except TelegramForbiddenError as e:
        logging.error(f"Target [ID:{user_id}]: blocked by user")
    except TelegramNotFound as e:
        logging.error(f"Target [ID:{user_id}]: invalid user ID")
    except TelegramAPIError as e:
        logging.exception(f"Target [ID:{user_id}]: failed")
    else:
        return True

    return False


@dp.message(BroadcastState.distrib_message)
async def get_broadcast_message(message: types.Message, state: FSMContext) -> None:
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
    logging.info(f"Start broadcast message for {len(all_users)} users.")
    count = 0
    try:
        for user in all_users:
            if await broadcaster(user.user_id, broadcast_data):
                count += 1
            await asyncio.sleep(.05)
    finally:
        logging.info(f"{count} messages successful sent.")


def get_user_title(user_data: TgUser) -> str | int:
    if user_data.username != None:
        return user_data.username
    elif user_data.full_name != None:
        return user_data.full_name
    else:
        return user_data.id


@dp.message(Command("support"))
async def support_chat(message: types.Message) -> None:
    msg = "Для получения более подробной информаци " +\
        f"или услуге Вы можете отправить сообщение на " +\
        "запрос в чате ниже или на почту support@bimmer-online.ru"

    user = get_user_title(message.from_user)    

    chat_name = f"{user} запрос поддержки"

    link = await create_chat(message.from_user.id, chat_name, "support_chat")

    msg = f"По вашему запросу поддержки был создан чат, ссылка на чат {link}"
    await message.answer(
        msg
    )
    logging.info(f"User {message.from_user.id} get chat link - {link}")


@dp.callback_query(ChatType.filter(F.con_type == "OnlySupportChats"))
async def only_support_chats(callback: CallbackQuery, callback_data: ChatType) -> None:
    chat_type = ""
    if callback_data.chat_type == "OrderParts":
        chat = order_chats
    elif callback_data.chat_type == "Support":
        if callback_data.key in support_chats.keys():
            chat = support_chats
        else:
            chat = coding_services_chats
    elif callback_data.chat_type == "DiagEquip":
        chat = diag_equip_chats
        chat_type = "оборудованию"

        if chat[callback_data.key] != "Написать запрос на оборудование":
            await callback.message.answer_photo(
                types.FSInputFile(path=path_photos + equip_photos[callback_data.key]),
                caption=diag_equip_chats[callback_data.key]
            )

    if chat_type == "":
        if support_chats_type[callback_data.key] == "продукт":
            chat_type = "продукту"
        else:
            chat_type = "услуге"

    msg = f"Для получения более подробной информации по {chat_type} " +\
    f"\"{chat[callback_data.key]}\" Вы можете отправить сообщение на " +\
    "запрос в чате ниже или на почту support@bimmer-online.ru"
    builder = InlineKeyboardBuilder()
    callback_data.con_type = "CreateChat"

    builder.row(
        types.InlineKeyboardButton(
            text="Создать чат с поддержкой",
            callback_data=callback_data.pack())
        )
    
    if callback_data.chat_type == "OrderParts" and callback_data.key == "chat3":
        msg = "Уважаемые клиенты, перед отправкой запроса на поиск детали просьба ознакомиться с правилами заказа:\n" +\
        "1) Сроки поставки составляют от 2-х месяцев\n" +\
        "2) Вес одной детали не более 30 кг\n" +\
        "3) Максимальные габаритные размеры упаковки не должны превышать 180x60x60 см"
    elif callback_data.chat_type == "OrderParts" and (callback_data.key == "chat1" or callback_data.key == "chat2"):
        msg = "Напишите в чат Ваш запрос с указанием артикула детали и VIN номера автомобиля"

    
    await callback.message.answer(
        msg,
        reply_markup=builder.as_markup()
    )


async def create_chat(user_id: int, chat_name: str, contract_type: str) -> str:
    get_chat = await SupportChat.get_or_none(
        contract_type=contract_type,
        user_id=user_id
    )

    if get_chat != None:
        try:
            await client(functions.messages.CheckChatInviteRequest(hash=get_chat.link.split("/")[-1][1:]))
        except BadRequestError:
            await get_chat.delete()
            logging.info(f"Chat with id {get_chat.chat_id} was deleted! Сreate new chat.")
            get_chat = None

    if get_chat == None:
        user_entity = await client.get_input_entity(user_id)

        result = await client(functions.messages.CreateChatRequest(
            users=[*support_users, user_entity],
            title=chat_name
        ))

        chat_id = result.updates.updates[1].participants.chat_id

        chat = await client.get_entity(telethonTypes.PeerChat(chat_id))   
        chat_link = await client(functions.messages.ExportChatInviteRequest(
            peer=chat
        ))
        
        await SupportChat.create(
            chat_id=chat_id,
            contract_type=contract_type,
            chat_name=chat_name,
            link=chat_link.link,
            user_id=user_id
        )

        return chat_link.link
    
    return get_chat.link


@dp.callback_query(ChatType.filter(F.con_type == "CreateChat"))
async def create_support_chats(callback: CallbackQuery, callback_data: ChatType) -> None:
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

    chat_name = f"{user} продукт {chat[callback_data.key]}"

    if callback_data.chat_type == "DiagEquip" and callback_data.key == "chat5":
        chat_name = f"{user} запрос на оборудование"

    link = await create_chat(callback.from_user.id, chat_name, chat[callback_data.key])

    msg = f"По вашему запросу продукта {chat[callback_data.key]} был создан чат, ссылка на чат {link}"
    await callback.message.answer(
        msg
    )
    logging.info(f"User {callback.from_user.id} get chat link - {link}")


@dp.callback_query(ChatType.filter(F.con_type == "OnlyChannelChats"))
async def only_channel_chats(callback: CallbackQuery, callback_data: ChatType, state: FSMContext) -> None:
    get_perm = await AccesChannelUser.get_or_none(
        user_id=callback.from_user.id, 
        product=channel_chats[callback_data.key],
        permission=True
    )

    if get_perm != None:
        msg = f"Ссылка для подключения к чату по программе {channel_chats[callback_data.key]}\n" +\
            f"{channel_links[callback_data.key]}"
        
        await callback.message.answer(
            msg
        )
        return
    
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
    product = data.get("product")
    email = data.get("email")
    sto_name = data.get("sto_name")
    await state.clear()

    get_user = await User.get_or_none(
        user_id=message.from_user.id
    )

    user_title = ""
    if get_user != None:
        if get_user.username:
            user_title = get_user.username
        elif get_user.fullname:
            user_title = get_user.fullname
        else:
            user_title = get_user.user_id

    msg = f"Пользователь {user_title} запрашивает доступ к каналу " +\
        f"{product} по указанным данным (emal\название СТО)\n" +\
        f"{email}\n{sto_name}"

    find_user = await client(functions.users.GetFullUserRequest(
        id=list(moderators.values())[0]
    ))
    moderator_id = find_user.full_user.id

    position = val_chan_list.index(product)

    await AccesChannelUser.create(
        product=product,
        email=email,
        sto_name=sto_name,
        permission=False,
        user_id=message.from_user.id
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Предоставить ссылку",
            callback_data=AccesData(user_id=message.from_user.id,
                                    product=key_chan_list[position],
                                    permission=True).pack()),
        types.InlineKeyboardButton(
            text="НЕ предоставлять ссылку",
            callback_data=AccesData(user_id=message.from_user.id,
                                    product=key_chan_list[position],
                                    permission=False).pack()),
    )

    await message.answer("Ожидайте ответа модератора.") 

    await bot.send_message(
        chat_id=moderator_id,
        text=msg,
        reply_markup=builder.as_markup()
    )


@dp.callback_query(AccesData.filter(F.permission == True))
async def grant_permission(callback: CallbackQuery, callback_data: AccesData) -> None:
    get_perm = await AccesChannelUser.get_or_none(
        user_id=callback_data.user_id, 
        product=channel_chats[callback_data.product],
        permission=False
    )

    if get_perm != None:
        get_perm.permission = True
        await get_perm.save()
    else:
        logging.warning(f"Can't find record in acces_channel_users for User {callback_data.user_id}" +\
                        f" and Product {channel_chats[callback_data.product]}")
        await callback.message.answer(f"Ошибка! Пользователь c ID {callback_data.user_id} с продуктом " +\
                            f"{channel_chats[callback_data.product]} не был найден в базе данных!")

        return

    msg = f"Ссылка для подключения к чату по программе {channel_chats[callback_data.product]}\n" +\
        f"{channel_links[callback_data.product]}"

    await callback.message.answer("Принят")

    await bot.send_message(
        chat_id=callback_data.user_id,
        text=msg
    )

    find_admin_user = await client(functions.users.GetFullUserRequest(
        id=list(admin.values())[0]
    ))

    await bot.send_message(
        chat_id=find_admin_user.full_user.id,
        text=f"Новый запрос на подключение в группу {channel_chats[callback_data.product]}."
    )


@dp.callback_query(AccesData.filter(F.permission == False))
async def decline_permission(callback: CallbackQuery, callback_data: AccesData) -> None:
    get_perm = await AccesChannelUser.get_or_none(
        user_id=callback_data.user_id, 
        product=channel_chats[callback_data.product],
        permission=False
    )

    if get_perm != None:
        await get_perm.delete()
    else:
        await callback.message.answer("Решение по данному клиенту было принято ранее!")
        return

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
    await Tortoise.init(tortoise_orm_config)

    add_button_keys(all_program_keys, channel_chats, "OnlyChannelChats", "Channel", 15, 2)
    add_button_keys(all_program_keys, support_chats, "OnlySupportChats", "Support", 13, 2)
    add_button_keys(coding_services_keys, coding_services_chats, "OnlySupportChats", "Support", 13, 2)
    add_button_keys(order_parts_keys, order_chats, "OnlySupportChats", "OrderParts", 15, 2)
    add_button_keys(diag_equip_keys, diag_equip_chats, "OnlySupportChats", "DiagEquip", 15, 2)

    dp.startup.register(set_menu)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
