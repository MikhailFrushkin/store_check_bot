"""
Вход в отдел: список артикулов на сегодня и карточки с кнопками отработки.
"""

from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message

from store_check_bot.config import settings
from store_check_bot.db.database import async_session
from store_check_bot.services.runtime_settings import get_runtime_settings
from store_check_bot.filters.admin import message_from_privileged
from store_check_bot.keyboards.main_menu import BTN_DEPT_PREFIX, back_keyboard, main_menu_keyboard
from store_check_bot.keyboards.product_inline import product_check_keyboard
from store_check_bot.repositories.products import get_user_verification, get_department_stats
from store_check_bot.services.daily_assignment import assign_daily_products, get_today_products
from store_check_bot.utils.formatting import format_department_header
from store_check_bot.utils.messages import send_product_card

router = Router()


@router.message(F.text.startswith(BTN_DEPT_PREFIX))
async def open_department(message: Message) -> None:
    """
    Показать артикулы, назначенные на сегодня в выбранном отделе.

    Если назначений ещё нет (после 06:00) — создать порцию из 10 шт.
    """
    if not message.text:
        return

    try:
        department = int(message.text.replace(BTN_DEPT_PREFIX, "").strip())
    except ValueError:
        await message.answer("Неверный номер отдела.")
        return

    if department < 1 or department > settings.departments_count:
        await message.answer(f"Отдел должен быть от 1 до {settings.departments_count}.")
        return

    user_id = message.from_user.id if message.from_user else 0
    today = datetime.now(settings.tz).date()

    async with async_session() as session:
        products = await get_today_products(session, department, today)

        # Если сегодня ещё не назначали — попробовать назначить (после 6:00 или вручную)
        if not products:
            runtime = await get_runtime_settings(session)
            now = datetime.now(settings.tz)
            if now.hour >= runtime.daily_assign_hour:
                await assign_daily_products(session, today, department)
                products = await get_today_products(session, department, today)

    if not products:
        await message.answer(
            f"На сегодня ({today.strftime('%d.%m.%Y')}) в отделе {department} "
            f"нет артикулов для проверки.\n"
            f"Назначение выполняется по расписанию (см. ⚙️ Настройки) "
            "или загрузите новый файл Excel.",
            reply_markup=back_keyboard(),
        )
        return

    data_dep = await get_department_stats(session, department)
    await message.answer(
        format_department_header(today, department, products, data_dep),
        reply_markup=back_keyboard(),
        parse_mode="HTML",
    )

    async with async_session() as session:
        for product in products:
            verification = await get_user_verification(session, product.id, user_id)
            status = verification.status if verification else None
            keyboard = product_check_keyboard(product.id, status)
            await send_product_card(message, product, status, keyboard)

    full_access = message_from_privileged(message)
    await message.answer(
        "Отметьте каждый артикул кнопками под сообщением.",
        reply_markup=main_menu_keyboard(full_access=full_access),
    )
