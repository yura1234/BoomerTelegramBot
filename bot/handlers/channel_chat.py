import re
import logging
from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import functions

from loader import config, client, bot
from bot.models.callback import ChatTypeCallback, AccesUserCallback
from bot.models.database import AccesChannelUser, User
from bot.models.state import UserState, ModeratorChannelState


router = Router()
logger = logging.getLogger(__name__)
channel_chats = config["allPrograms.OnlyChannelChats"]
channel_links = config["OnlyChannelLinks"]
key_chan_list = list(channel_chats.keys())
val_chan_list = list(channel_chats.values())


@router.callback_query(ChatTypeCallback.filter(F.con_type == "OnlyChannelChats"))
async def only_channel_chats(
    callback: CallbackQuery,
    callback_data: ChatTypeCallback,
    state: FSMContext
) -> None:
    get_perm = await AccesChannelUser.get_or_none(
        user_id=callback.from_user.id,
        product=channel_chats[callback_data.key],
        permission=True
    )

    if get_perm:
        msg = f"Ссылка для подключения к чату по программе {channel_chats[callback_data.key]}\n" +\
            f"{channel_links[callback_data.key]}"

        await callback.message.answer(
            msg
        )
        return

    msg = f"Для доступа в канал {channel_chats[callback_data.key]} необходимо указать" +\
        "Ваш рабочий email и название СТО.\nЛибо направьте запрос в поддержку."
    callback_data.con_type = "CreateChat"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Написать запрос",
            callback_data=callback_data.pack()
        )
    )

    await callback.message.answer(
        msg,
        reply_markup=builder.as_markup()
    )

    await callback.message.answer(
        "Укажите Ваш email:"
    )
    await state.update_data(product=channel_chats[callback_data.key])
    await state.set_state(UserState.email)


@router.message(UserState.email)
async def save_email(message: Message, state: FSMContext) -> None:
    email_valid_pattern = r"^\S+@\S+\.\S+$"

    if re.match(email_valid_pattern, message.text) is None:
        await message.answer("Пожалуйста введите корректный емайл адрес")
        return

    await state.update_data(email=message.text)

    await message.answer("Укажите название Вашей СТО:")
    await state.set_state(UserState.sto_name)


@router.message(UserState.sto_name)
async def save_sto(message: Message, state: FSMContext) -> None:
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
    if get_user:
        if get_user.username:
            user_title = get_user.username
        elif get_user.fullname:
            user_title = get_user.fullname
        else:
            user_title = get_user.user_id

    msg = f"Пользователь {user_title} запрашивает доступ к каналу " +\
        f"{product} по указанным данным (emal\название СТО)\n" +\
        f"{email}\n{sto_name}"

    find_user = await client(
        functions.users.GetFullUserRequest(
            id=list(config["Moderators"].values())[0]
        )
    )
    moderator_id = find_user.full_user.id

    position = val_chan_list.index(product)

    await AccesChannelUser.update_or_create(
        product=product,
        user_id=message.from_user.id,
        permission=False,
        defaults={
            "email":email,
            "sto_name":sto_name,
        }
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Предоставить ссылку",
            callback_data=AccesUserCallback(
                user_id=message.from_user.id,
                product=key_chan_list[position],
                permission=True,
                write_com=False
            ).pack()
        ),
        InlineKeyboardButton(
            text="НЕ предоставлять ссылку",
            callback_data=AccesUserCallback(
                user_id=message.from_user.id,
                product=key_chan_list[position],
                permission=False,
                write_com=False
            ).pack()
        ),
    )

    await message.answer("Ожидайте ответа модератора.") 

    await bot.send_message(
        chat_id=moderator_id,
        text=msg,
        reply_markup=builder.as_markup()
    )


@router.callback_query(AccesUserCallback.filter(F.permission == True))
async def grant_permission(callback: CallbackQuery, callback_data: AccesUserCallback) -> None:
    get_perm = await AccesChannelUser.get_or_none(
        user_id=callback_data.user_id,
        product=channel_chats[callback_data.product],
        permission=False
    )

    if get_perm:
        get_perm.permission = True
        await get_perm.save()
    else:
        logger.warning("Can't find record in acces_channel_users for User " +\
            f"{callback_data.user_id} and Product {channel_chats[callback_data.product]}")
        await callback.message.answer(f"Ошибка! Пользователь c ID {callback_data.user_id} с " +\
            f"продуктом {channel_chats[callback_data.product]} не был найден в базе данных!")
        return

    msg = f"Ссылка для подключения к чату по программе {channel_chats[callback_data.product]}\n" +\
        f"{channel_links[callback_data.product]}"

    await callback.message.answer("Принят")

    await bot.send_message(
        chat_id=callback_data.user_id,
        text=msg
    )


@router.callback_query(AccesUserCallback.filter(F.permission == False and F.write_com == False))
async def decline_permission(
    callback: CallbackQuery,
    callback_data: AccesUserCallback,
    state: FSMContext
) -> None:
    msg = "К сожалению, мы не нашли у Вашей СТО активной подписки на данную программу. " +\
        "Для приобретения доступа просим написать запрос на почту support@bimmer-online.ru " +\
        "или в чат поддержки @bimmeronline"

    await callback.message.answer("Отклонен")
    await bot.send_message(
        chat_id=callback_data.user_id,
        text=msg
    )

    callback_data_btn = callback_data.model_copy()
    callback_data_btn.write_com = True

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Указать причину",
            callback_data=callback_data_btn.pack()
        )
    )

    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Вы можете указать причину отказа нажав кнопку ниже",
        reply_markup=builder.as_markup()
    )


@router.callback_query(AccesUserCallback.filter(F.write_com == True))
async def write_decline_comment(
    callback: CallbackQuery,
    callback_data: AccesUserCallback,
    state: FSMContext
) -> None:
    await callback.message.answer("Введите причину отказа:")
    await state.update_data(user_id=callback_data.user_id)
    await state.update_data(product=channel_chats[callback_data.product])
    await state.set_state(ModeratorChannelState.decline_comment)


@router.message(ModeratorChannelState.decline_comment)
async def decline_comment_moderator(message: Message, state: FSMContext) -> None:
    dec_comment = message.text

    data = await state.get_data()
    user_id = int(data.get("user_id"))
    product = data.get("product")
    await state.clear()

    await bot.send_message(
        user_id,
        f"Ответ модератора по вашему запросу в чат {product}:\n" +\
        dec_comment
    )

    get_perm = await AccesChannelUser.get_or_none(
        user_id=user_id,
        product=product,
        permission=False
    )

    if get_perm:
        get_perm.decline_comment = dec_comment
        await get_perm.save()
    else:
        logger.warning(f"Can't find record in acces_channel_users for User {user_id}" +\
                        f" and Product {channel_chats[product]}")
        await message.answer(f"Ошибка! Пользователь c ID {user_id} с продуктом " +\
                            f"{channel_chats[product]} не был найден в базе данных!")
