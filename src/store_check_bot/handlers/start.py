"""
Старт бота и регистрация пользователя для рассылок.
"""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from store_check_bot.db.database import async_session
from store_check_bot.filters.admin import message_from_privileged
from store_check_bot.keyboards.main_menu import BTN_BACK, main_menu_keyboard
from store_check_bot.repositories.bot_users import register_bot_user

router = Router()


@router.message(CommandStart())
@router.message(Command("menu"))
@router.message(F.text == BTN_BACK)
async def cmd_start(message: Message) -> None:
    """
    Главное меню проверки неучтённого товара.

    Пользователь попадает в список рассылки сводок (10, 12, 14, 16).
    """
    if message.from_user:
        async with async_session() as session:
            await register_bot_user(session, message.from_user)

    full_access = message_from_privileged(message)
    await message.answer(
        "Бот проверки <b>неучтённого товара</b>.\n"
        "Выберите отдел — покажем артикулы на сегодня (до 10 шт.).",
        reply_markup=main_menu_keyboard(full_access=full_access),
    )
