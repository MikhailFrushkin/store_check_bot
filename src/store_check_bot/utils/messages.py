"""
Отправка текстовой карточки артикула (фото не используются).
"""

from aiogram.types import InlineKeyboardMarkup, Message

from store_check_bot.db.models import Product
from store_check_bot.utils.formatting import product_caption


async def send_product_card(
    message: Message,
    product: Product,
    status: str | None,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """Отправить карточку артикула только текстом с инлайн-кнопками."""
    caption = product_caption(product, status)
    await message.answer(caption, reply_markup=keyboard, parse_mode="HTML")
