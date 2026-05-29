"""Инлайн-клавиатура меню настроек."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_PREFIX = "settings"

CB_ASSIGN_HOUR = f"{CALLBACK_PREFIX}:assign_hour"
CB_SUMMARY_HOURS = f"{CALLBACK_PREFIX}:summary_hours"
CB_PRODUCTS_PER_DAY = f"{CALLBACK_PREFIX}:products_per_day"
CB_CANCEL = f"{CALLBACK_PREFIX}:cancel"


def settings_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопки выбора параметра для изменения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🕕 Время обновления артикулов",
                    callback_data=CB_ASSIGN_HOUR,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📢 Часы сводки",
                    callback_data=CB_SUMMARY_HOURS,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔢 Артикулов в день на отдел",
                    callback_data=CB_PRODUCTS_PER_DAY,
                ),
            ],
            [
                InlineKeyboardButton(text="◀️ Закрыть", callback_data=CB_CANCEL),
            ],
        ]
    )
