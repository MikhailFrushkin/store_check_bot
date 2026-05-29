"""
Загрузка Excel и отчёт «Результаты».
"""

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from store_check_bot.config import settings
from store_check_bot.db.database import async_session
from store_check_bot.filters.admin import message_from_privileged
from store_check_bot.keyboards.main_menu import BTN_RESULTS, BTN_UPLOAD, BTN_SETTINGS, main_menu_keyboard
from store_check_bot.repositories.products import get_all_stats
from store_check_bot.services.daily_assignment import assign_daily_products
from store_check_bot.services.excel_export import build_results_workbook
from store_check_bot.services.excel_import import import_products_to_db, parse_products_from_excel
from store_check_bot.states import UploadStates
from store_check_bot.utils.formatting import format_stats_message

router = Router()

UPLOAD_DIR = Path("data/uploads")
EXPORT_DIR = Path("data/exports")


@router.message(F.text == BTN_UPLOAD)
async def start_upload(message: Message, state: FSMContext) -> None:
    """Запросить файл Excel (формат «Неучтенные товары»)."""
    if not message_from_privileged(message):
        await message.answer("Доступно только администраторам.")
        return

    await state.set_state(UploadStates.waiting_file)
    await message.answer(
        "Отправьте Excel <b>Неучтенные товары.xlsx</b> (.xlsx).\n\n"
        "Колонки как в выгрузке: Магазин, Отдел, Подотдел, Артикул, "
        "Наименование, LOC, …\n\n"
        "При загрузке сбрасывается очередь показа артикулов.\n\n"
        "Для отмены нажмите /menu",
        parse_mode="HTML",
    )


@router.message(StateFilter(UploadStates.waiting_file), F.document)
async def process_upload(message: Message, state: FSMContext) -> None:
    """Импорт файла и назначение первых 10 артикулов на сегодня по отделам."""
    if not message_from_privileged(message):
        await message.answer("Доступно только администраторам.")
        await state.clear()
        return

    if not message.document:
        return

    if not message.document.file_name or not message.document.file_name.lower().endswith(
        (".xlsx", ".xls")
    ):
        await message.answer("Нужен файл Excel (.xlsx).")
        return

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / message.document.file_name
    await message.bot.download(message.document, destination=file_path)

    try:
        products = parse_products_from_excel(file_path)
    except ValueError as exc:
        await message.answer(f"Ошибка в файле: {exc}")
        return
    finally:
        file_path.unlink(missing_ok=True)
        await state.clear()

    async with async_session() as session:
        count = await import_products_to_db(session, products)
        assigned = await assign_daily_products(session)

    await message.answer(
        f"Загружено артикулов: {count}.\n"
        f"Назначено на сегодня: {assigned} арт.\n"
        "Очередь показа сброшена — повторы до следующей загрузки исключены.",
        reply_markup=main_menu_keyboard(full_access=True),
    )


@router.message(StateFilter(UploadStates.waiting_file), F.text == BTN_RESULTS)
async def upload_cancel_for_results(message: Message, state: FSMContext) -> None:
    """Отмена загрузки при нажатии на кнопку Результаты."""
    await state.clear()
    # Вызываем обработчик результатов
    await show_results(message)


@router.message(StateFilter(UploadStates.waiting_file), F.text == BTN_SETTINGS)
async def upload_cancel_for_settings(message: Message, state: FSMContext) -> None:
    """Отмена загрузки при нажатии на кнопку Настройки."""
    await state.clear()
    await message.answer(
        "Загрузка файла отменена.",
        reply_markup=main_menu_keyboard(full_access=True)
    )


@router.message(StateFilter(UploadStates.waiting_file), F.text == "/menu")
async def upload_cancel_menu(message: Message, state: FSMContext) -> None:
    """Отмена загрузки по команде /menu."""
    await state.clear()
    await message.answer(
        "Загрузка файла отменена.",
        reply_markup=main_menu_keyboard(full_access=True)
    )


@router.message(StateFilter(UploadStates.waiting_file))
async def upload_wrong_type(message: Message) -> None:
    """В режиме загрузки принимаем только документ."""
    await message.answer(
        "Отправьте .xlsx или нажмите /menu для отмены."
    )


@router.message(F.text == BTN_RESULTS)
async def show_results(message: Message) -> None:
    """Статистика за сегодня и файл Excel."""
    if not message_from_privileged(message):
        await message.answer("Доступно только администраторам.")
        return
    async with async_session() as session:
        stats = await get_all_stats(session, settings.departments_count)
        export_path = await build_results_workbook(session, EXPORT_DIR)

    await message.answer(format_stats_message(stats), parse_mode="HTML")
    await message.answer_document(
        FSInputFile(export_path),
        caption="Результаты отработки неучтённого товара",
    )