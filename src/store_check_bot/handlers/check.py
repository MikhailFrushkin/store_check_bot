"""
Обработка «Отработан» / «Не отработан» и сообщение о завершении дня по отделу.
"""

from datetime import datetime

from aiogram import Router
from aiogram.types import CallbackQuery

from store_check_bot.config import settings
from store_check_bot.db.database import async_session
from store_check_bot.keyboards.product_inline import parse_check_callback, product_check_keyboard
from store_check_bot.repositories.products import get_product, upsert_verification
from store_check_bot.services.daily_assignment import all_today_processed
from store_check_bot.utils.formatting import product_caption

router = Router()

COMPLETION_MESSAGE = "Все артикула на сегодня отработаны, хорошая работа 👍"


@router.callback_query(lambda c: c.data and c.data.startswith("check:"))
async def on_product_check(callback: CallbackQuery) -> None:
    """Сохранить отметку и обновить карточку; при полной отработке — поздравление."""
    if not callback.data or not callback.from_user:
        await callback.answer("Ошибка данных")
        return

    parsed = parse_check_callback(callback.data)
    if not parsed:
        await callback.answer("Неверная кнопка")
        return

    product_id, status = parsed
    user = callback.from_user
    full_name = user.full_name or user.username or str(user.id)

    department: int | None = None

    async with async_session() as session:
        product = await get_product(session, product_id)
        if not product:
            await callback.answer("Артикул не найден")
            return

        department = product.department

        await upsert_verification(
            session,
            product_id=product_id,
            user_id=user.id,
            username=user.username,
            full_name=full_name,
            status=status,
        )

        completed = False
        if status.value == "processed" and department is not None:
            completed = await all_today_processed(session, department)

    keyboard = product_check_keyboard(product_id, status.value)
    caption = product_caption(product, status.value)

    if callback.message:
        await callback.message.edit_text(
            text=caption,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    label = "✅ Отработан" if status.value == "processed" else "❌ Не отработан"
    await callback.answer(f"Сохранено: {label}")

    if completed and callback.message:
        await callback.message.answer(COMPLETION_MESSAGE)
