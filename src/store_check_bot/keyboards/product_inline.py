"""
Инлайн-кнопки «Отработан» / «Не отработан» под карточкой артикула.

callback_data: check:{product_id}:p|n
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from store_check_bot.db.models import VerificationStatus

CALLBACK_PREFIX = "check"
ACTION_PROCESSED = "p"
ACTION_NOT_PROCESSED = "n"


def _btn_label(base: str, selected: bool) -> str:
    """Визуально выделить выбранную кнопку."""
    return f"· {base} ·" if selected else base


def product_check_keyboard(
    product_id: int,
    current_status: str | None,
) -> InlineKeyboardMarkup:
    """Клавиатура отработки артикула."""
    processed_selected = current_status == VerificationStatus.PROCESSED.value
    not_processed_selected = current_status == VerificationStatus.NOT_PROCESSED.value

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_btn_label("✅ Отработан", processed_selected),
                    callback_data=f"{CALLBACK_PREFIX}:{product_id}:{ACTION_PROCESSED}",
                ),
                InlineKeyboardButton(
                    text=_btn_label("❌ Не отработан", not_processed_selected),
                    callback_data=f"{CALLBACK_PREFIX}:{product_id}:{ACTION_NOT_PROCESSED}",
                ),
            ],
        ]
    )


def parse_check_callback(data: str) -> tuple[int, VerificationStatus] | None:
    """Разобрать callback_data кнопки."""
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CALLBACK_PREFIX:
        return None
    try:
        product_id = int(parts[1])
    except ValueError:
        return None
    if parts[2] == ACTION_PROCESSED:
        return product_id, VerificationStatus.PROCESSED
    if parts[2] == ACTION_NOT_PROCESSED:
        return product_id, VerificationStatus.NOT_PROCESSED
    return None
