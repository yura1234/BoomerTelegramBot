from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

from bot.models.callback import ChatTypeCallback


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
                callback_data=ChatTypeCallback(
                    key=chat_keys[i], 
                    con_type=callback_type,
                    chat_type=chat_type).pack()
                )
            )
            i += 1
            w += 1
        elif len(chats[chat_keys[i]]) >= max_len:
            if len(keys_arr) > 0:
                builder.row(*keys_arr, width=width)
                keys_arr = []

            keys_arr.append(
                types.InlineKeyboardButton(
                text=chats[chat_keys[i]],
                callback_data=ChatTypeCallback(
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
