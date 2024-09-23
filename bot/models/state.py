from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    product = State()
    email = State()
    sto_name = State()


class BroadcastState(StatesGroup):
    distrib_message = State()
    edit_message = State()