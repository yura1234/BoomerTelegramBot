from aiogram.filters.callback_data import CallbackData


class ChatTypeCallback(CallbackData, prefix="con"):
    key: str
    con_type: str
    chat_type: str


class AccesUserCallback(CallbackData, prefix="acc"):
    user_id: int
    product: str
    permission: bool


class BroadcastMenuCallback(CallbackData, prefix="brd"):
    broad_type: str
    id: int = -1


class BroadcastBtnCallback(CallbackData, prefix="brdbtn"):
    id: int