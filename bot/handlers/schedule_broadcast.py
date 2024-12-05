import logging
import asyncio
import re
from datetime import date, datetime, timedelta
from tortoise import timezone
from tortoise.expressions import Q
import pytz
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram import Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram_dialog.widgets.text import Const
from aiogram_dialog import Dialog, DialogManager, StartMode, Window

from bot.models.database import BroadcastData
from bot.models.callback import DateTimeCallback, BroadcastMenuCallback
from bot.models.state import BroadcastState, CalendarState, TimeState
from bot.keyboards.custom_calendar import CustomCalendar


router = Router()
logger = logging.getLogger(__name__)


async def on_date_selected(
    callback: CallbackQuery,
    widget,
    manager: DialogManager,
    selected_date: date,
) -> None:
    if manager.start_data:
        broadcast = await BroadcastData.filter(id=manager.start_data["id"]).first()
        if broadcast:
            broadcast.created_date = broadcast.created_date.replace(
                day=selected_date.day,
                month=selected_date.month,
                year=selected_date.year
            )
            await broadcast.save()
            await callback.message.answer(
                "Дата у отложенного сообщения была изменена на "
                f"{selected_date.strftime("%d.%m.%Y")}"
            )
        await manager.reset_stack()
        asyncio.create_task(remake_schedule_task(broadcast))
        return

    await manager.reset_stack()

    builder = InlineKeyboardBuilder()
    str_date = selected_date.strftime("%d-%m-%Y")

    builder.row(
        InlineKeyboardButton(
            text="Указать время",
            callback_data=DateTimeCallback(schedule_date=str_date).pack()
        )
    )
    await callback.message.answer(
        f"Укажите время на дату {str_date}",
        reply_markup=builder.as_markup()
    )


calendar = CustomCalendar(
    id='calendar',
    on_click=on_date_selected
)
main_window = Window(
    Const("Выбор даты"),
    calendar,
    state=CalendarState.main,
)
dialog = Dialog(main_window)


@router.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Schedule"))
async def create_schedule_broadcast_message(callback: CallbackQuery, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(CalendarState.main, mode=StartMode.RESET_STACK)


@router.callback_query(DateTimeCallback.filter(F.schedule_date))
async def set_schedule_time_state(
    callback: CallbackQuery,
    callback_data: DateTimeCallback,
    state: FSMContext
) -> None:
    await callback.message.answer(
        "Введите время в формате ЧЧ ММ"
    )
    await state.update_data(schedule_date=callback_data.schedule_date)
    await state.set_state(TimeState.time)


@router.message(TimeState.time)
async def get_schedule_time(message: Message, state: FSMContext) -> None:
    time_pattern = r"^(2[0-3]|[01]?[0-9]) ([0-5]?[0-9])$"

    if re.match(time_pattern, message.text) is None:
        await message.answer("Пожалуйста введите корректное время!")
        return

    edit_time_id = (await state.get_data()).get("edit_id")
    if edit_time_id:
        await state.update_data(edit_id=0)
        time = message.text.split()
        broadcast = await BroadcastData.filter(id=edit_time_id).first()
        if broadcast:
            broadcast.created_date = broadcast.created_date.replace(
                hour=int(time[0]),
                minute=int(time[1])
            )
            await broadcast.save()
            await message.answer(
                "Время у отложенного сообщения было изменено на "
                f"{message.text}"
            )
            asyncio.create_task(remake_schedule_task(broadcast))
            return

    current_time = timezone.now()
    datetime_parts = [
        *(await state.get_data()).get("schedule_date").split("-")[::-1],
        *message.text.split()
    ]
    schedule_time = current_time.replace(*list(map(int, datetime_parts)))
    if current_time > schedule_time:
        await message.answer(
            "Время отложенной новости не может быть меньше текущего времени!\n"
            "Укажите другое время."
        )
        return

    schedule_intersections = await BroadcastData.filter(
        Q(created_date__gte = schedule_time.replace(second=0))\
        & Q(created_date__lte = schedule_time.replace(second=59))
    )
    if schedule_intersections:
        await message.answer(
            "На выбранную дату и время уже есть отложенная новость!\n"
            "Укажите другое время."
        )
        return

    await state.update_data(schedule_time=message.text)
    await message.answer(
        "Выберете отложенное сообщение для массовой рассылки пользователям:"
    )
    await state.set_state(BroadcastState.distrib_message)


async def task_sceduled_data(data: BroadcastData, offset_time: int = None) -> None:
    from .admin import broadcast_for_all
    current_datetime = datetime.now(pytz.timezone("Europe/Moscow"))

    if data.created_date < current_datetime:
        task_time = current_datetime + timedelta(minutes=offset_time)
    else:
        task_time = data.created_date

    logger.info(
        "Add sceduled task at %s for broadcast id %d",
        task_time.strftime("%d_%m_%Y-%H_%M_%S"),
        data.id
    )
    seconds_to_start = (task_time - current_datetime).seconds
    try:
        await asyncio.sleep(seconds_to_start)
    except asyncio.CancelledError:
        logger.info("Cancel task with id %s", data.id)
        return

    await broadcast_for_all(data)

    data.is_sheduled = False
    await data.save()


async def remake_schedule_task(data: BroadcastData) -> None:
    task_pattern = r"^[0-9]* schedule task"
    for task in asyncio.all_tasks():
        if re.match(task_pattern, task.get_name()):
            task.cancel()
            await task_sceduled_data(data)
            break


async def load_scheduled_broadcast_data() -> None:
    sceduled_data = await BroadcastData.filter(is_sheduled=True)
    offset_time = 5
    if sceduled_data:
        sceduled_tasks = []
        for data in sceduled_data:
            if data.created_date < timezone.now():
                sceduled_tasks.append(
                    asyncio.create_task(
                        coro=task_sceduled_data(data, offset_time),
                        name=f"{data.id} schedule task"
                    )
                )
                offset_time += 5
            else:
                sceduled_tasks.append(
                    asyncio.create_task(
                        coro=task_sceduled_data(data),
                        name=f"{data.id} schedule task"
                    )
                )
        await asyncio.gather(*sceduled_tasks)


@router.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Edit date"))
async def edit_date_schedule(
    callback: CallbackQuery,
    callback_data: BroadcastMenuCallback,
    dialog_manager: DialogManager
) -> None:
    await dialog_manager.start(
        CalendarState.main,
        mode=StartMode.RESET_STACK,
        data={"id": callback_data.id}
    )


@router.callback_query(BroadcastMenuCallback.filter(F.broad_type == "Edit time"))
async def edit_time_schedule(
    callback: CallbackQuery,
    callback_data: BroadcastMenuCallback,
    state: FSMContext
):
    await state.update_data(edit_id=callback_data.id)
    await callback.message.answer(
        "Введите время в формате ЧЧ ММ"
    )
    await state.set_state(TimeState.time)
