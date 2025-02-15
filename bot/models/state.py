from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    product = State()
    email = State()
    sto_name = State()


class ModeratorChannelState(StatesGroup):
    user_id = State()
    product = State()
    decline_comment = State()


class BroadcastState(StatesGroup):
    distrib_message = State()
    edit_message = State()


class CalendarState(StatesGroup):
    main = State()


class TimeState(StatesGroup):
    time = State()
