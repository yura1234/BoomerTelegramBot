from aiogram import Bot, Router
from aiogram.filters.command import Command
from aiogram.types import Message, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.buttons import add_button_keys
from loader import config


router = Router()
all_program_keys = InlineKeyboardBuilder()
coding_services_keys = InlineKeyboardBuilder()
order_parts_keys = InlineKeyboardBuilder()
diag_equip_keys = InlineKeyboardBuilder()
add_button_keys(all_program_keys,
                config["allPrograms.OnlyChannelChats"],
                "OnlyChannelChats", "Channel", 15, 2)
add_button_keys(all_program_keys,
                config["allPrograms.OnlySupportChats"],
                "OnlySupportChats", "Support", 13, 2)
add_button_keys(coding_services_keys,
                config["allPrograms.CodingServicesChats"],
                "OnlySupportChats", "Support", 13, 2)
add_button_keys(order_parts_keys,
                config["orderParts"],
                "OnlySupportChats", "OrderParts", 15, 2)
add_button_keys(diag_equip_keys,
                config["diagEquipment"],
                "OnlySupportChats", "DiagEquip", 15, 2)


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


@router.message(Command("diag_equipment"))
async def diag_equipment(message: Message) -> None:
    await message.answer(
        "Выберете необходимое оборудование для покупки",
        reply_markup=diag_equip_keys.as_markup()
    )


@router.message(Command("all_programs"))
async def all_programs(message: Message) -> None:
    await message.answer(
        "Выберете необходимую программу или услугу",
        reply_markup=all_program_keys.as_markup()
    )


@router.message(Command("coding_services"))
async def all_programs(message: Message) -> None:
    await message.answer(
        "Выберете необходимую программу или услугу",
        reply_markup=coding_services_keys.as_markup()
    )


@router.message(Command("order_parts"))
async def order_parts(message: Message) -> None:
    await message.answer(
        "Выберете необходимую программу или услугу",
        reply_markup=order_parts_keys.as_markup()
    )