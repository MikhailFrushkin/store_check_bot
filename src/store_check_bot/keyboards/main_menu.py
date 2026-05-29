"""
Reply-клавиатуры (кнопки под полем ввода).

Главное меню: сетка «Отдел 1» … «Отдел 15» (по 5 в ряд).
Для full_access=True добавляется второй ряд: загрузка и результаты.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from store_check_bot.config import settings

# Тексты кнопок должны совпадать с фильтрами в handlers (F.text)
BTN_UPLOAD = "📤 Загрузить файл"
BTN_RESULTS = "📊 Результаты"
BTN_SETTINGS = "⚙️ Настройки"
BTN_BACK = "◀️ Главное меню"
BTN_DEPT_PREFIX = "Отдел "


def main_menu_keyboard(full_access: bool = False) -> ReplyKeyboardMarkup:
    """
    Собрать главное меню.

    Args:
        full_access: Показать кнопки администратора (загрузка, отчёт).

    Returns:
        ReplyKeyboardMarkup с отделами и опционально админ-кнопками.
    """
    rows: list[list[KeyboardButton]] = []
    dept_buttons: list[KeyboardButton] = []

    for dept in range(1, settings.departments_count + 1):
        dept_buttons.append(KeyboardButton(text=f"{BTN_DEPT_PREFIX}{dept}"))
        if len(dept_buttons) == 5:
            rows.append(dept_buttons)
            dept_buttons = []
    if dept_buttons:
        rows.append(dept_buttons)

    if full_access:
        rows.append(
            [
                KeyboardButton(text=BTN_UPLOAD),
                KeyboardButton(text=BTN_RESULTS),
            ]
        )
        rows.append([KeyboardButton(text=BTN_SETTINGS)])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите отдел",
    )


def back_keyboard() -> ReplyKeyboardMarkup:
    """Упрощённая клавиатура при просмотре списка товаров отдела."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )
