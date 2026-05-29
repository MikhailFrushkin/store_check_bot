"""
Меню «Настройки» для администраторов: расписание и лимит артикулов в день.
"""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from store_check_bot.db.database import async_session
from store_check_bot.filters.admin import message_from_privileged
from store_check_bot.keyboards.main_menu import BTN_SETTINGS, main_menu_keyboard
from store_check_bot.keyboards.settings_inline import (
    CB_ASSIGN_HOUR,
    CB_CANCEL,
    CB_PRODUCTS_PER_DAY,
    CB_SUMMARY_HOURS,
    settings_menu_keyboard,
)
from store_check_bot.services.runtime_settings import (
    get_runtime_settings,
    save_runtime_settings,
    validate_summary_hours,
)
from store_check_bot.services.scheduler import reschedule_scheduler
from store_check_bot.states import SettingsStates

router = Router()


def _format_settings_text(runtime) -> str:
    """Текст с текущими настройками."""
    return (
        "<b>⚙️ Настройки бота</b>\n\n"
        f"🕕 Обновление артикулов: <b>{runtime.daily_assign_hour:02d}:00</b>\n"
        f"📢 Часы сводки: <b>{runtime.summary_hours}</b>\n"
        f"🔢 Артикулов в день (на отдел): <b>{runtime.products_per_day}</b>\n\n"
        "Выберите параметр для изменения:"
    )


@router.message(F.text == BTN_SETTINGS)
async def open_settings(message: Message, state: FSMContext) -> None:
    """Показать текущие настройки и кнопки редактирования."""
    if not message_from_privileged(message):
        await message.answer("Доступно только администраторам.")
        return

    await state.clear()
    async with async_session() as session:
        runtime = await get_runtime_settings(session)

    await message.answer(
        _format_settings_text(runtime),
        reply_markup=settings_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == CB_CANCEL)
async def settings_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Закрыть меню настроек."""
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Настройки закрыты.")
    await callback.answer()


@router.callback_query(F.data == CB_ASSIGN_HOUR)
async def settings_edit_assign_hour(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить новый час обновления артикулов (0–23)."""
    if not message_from_privileged(callback):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(SettingsStates.edit_assign_hour)
    if callback.message:
        await callback.message.answer(
            "Введите <b>час</b> обновления артикулов (0–23), например: <code>6</code>",
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == CB_SUMMARY_HOURS)
async def settings_edit_summary_hours(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить часы рассылки сводки."""
    if not message_from_privileged(callback):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(SettingsStates.edit_summary_hours)
    if callback.message:
        await callback.message.answer(
            "Введите <b>часы сводки</b> через запятую (0–23), "
            "например: <code>10,12,14,16</code>",
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == CB_PRODUCTS_PER_DAY)
async def settings_edit_products_per_day(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить число артикулов в день."""
    if not message_from_privileged(callback):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(SettingsStates.edit_products_per_day)
    if callback.message:
        await callback.message.answer(
            "Введите <b>сколько артикулов</b> выводить в день на отдел (1–100), "
            "например: <code>10</code>",
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(StateFilter(SettingsStates.edit_assign_hour), F.text)
async def save_assign_hour(message: Message, state: FSMContext) -> None:
    """Сохранить час обновления артикулов."""
    if not message_from_privileged(message) or not message.text:
        return

    try:
        hour = int(message.text.strip())
        if hour < 0 or hour > 23:
            raise ValueError
    except ValueError:
        await message.answer("Введите целое число от 0 до 23.")
        return

    async with async_session() as session:
        runtime = await save_runtime_settings(session, daily_assign_hour=hour)

    await reschedule_scheduler(message.bot)
    await state.clear()
    await message.answer(
        _format_settings_text(runtime) + "\n\n✅ Время обновления сохранено.",
        reply_markup=settings_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(SettingsStates.edit_summary_hours), F.text)
async def save_summary_hours(message: Message, state: FSMContext) -> None:
    """Сохранить часы сводки."""
    if not message_from_privileged(message) or not message.text:
        return

    try:
        validate_summary_hours(message.text.strip())
    except ValueError as exc:
        await message.answer(str(exc))
        return

    async with async_session() as session:
        runtime = await save_runtime_settings(session, summary_hours=message.text.strip())

    await reschedule_scheduler(message.bot)
    await state.clear()
    await message.answer(
        _format_settings_text(runtime) + "\n\n✅ Часы сводки сохранены.",
        reply_markup=settings_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(StateFilter(SettingsStates.edit_products_per_day), F.text)
async def save_products_per_day(message: Message, state: FSMContext) -> None:
    """Сохранить лимит артикулов в день."""
    if not message_from_privileged(message) or not message.text:
        return

    try:
        count = int(message.text.strip())
        if count < 1 or count > 100:
            raise ValueError
    except ValueError:
        await message.answer("Введите целое число от 1 до 100.")
        return

    async with async_session() as session:
        runtime = await save_runtime_settings(session, products_per_day=count)

    await state.clear()
    await message.answer(
        _format_settings_text(runtime) + "\n\n✅ Лимит артикулов сохранён.",
        reply_markup=settings_menu_keyboard(),
        parse_mode="HTML",
    )
