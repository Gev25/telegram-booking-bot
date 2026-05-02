from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_phone = State()


class Booking(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()


class AdminBroadcast(StatesGroup):
    waiting_message = State()
