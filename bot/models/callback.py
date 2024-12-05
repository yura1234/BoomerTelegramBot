from aiogram.filters.callback_data import CallbackData


class ChatTypeCallback(CallbackData, prefix="con"):
    key: str
    con_type: str
    chat_type: str


class AccesUserCallback(CallbackData, prefix="acc"):
    user_id: int
    product: str
    permission: bool
    write_com: bool


class BroadcastMenuCallback(CallbackData, prefix="brd"):
    broad_type: str
    id: int = -1
    schedule: bool = False


class BroadcastBtnCallback(CallbackData, prefix="brdbtn"):
    id: int
    schedule: bool = False


class DateTimeCallback(CallbackData, prefix="dtc"):
    schedule_date: str
