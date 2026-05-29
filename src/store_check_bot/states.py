"""
Состояния конечного автомата (FSM) Aiogram.

Используются для пошаговых сценариев, где бот ждёт определённый тип ввода.
"""

from aiogram.fsm.state import State, StatesGroup


class UploadStates(StatesGroup):
    """
    Сценарий загрузки каталога администратором.

    Переход: кнопка «Загрузить файл» → waiting_file → пользователь шлёт .xlsx.
    """

    waiting_file = State()  # ожидаем документ Excel


class SettingsStates(StatesGroup):
    """Редактирование расписания и лимитов в меню «Настройки»."""

    edit_assign_hour = State()
    edit_summary_hours = State()
    edit_products_per_day = State()
