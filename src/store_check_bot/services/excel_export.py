"""
Экспорт результатов отработки неучтённого товара в Excel.
"""

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from store_check_bot.repositories.products import get_verifications_for_export

STATUS_LABELS = {
    "processed": "Отработан",
    "not_processed": "Не отработан",
}


async def build_results_workbook(session: AsyncSession, export_dir: Path) -> Path:
    """Сформировать xlsx с отметками сотрудников."""
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = export_dir / f"results_{timestamp}.xlsx"

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Результаты"
    sheet.append(
        [
            "Отдел",
            "Артикул",
            "Наименование",
            "К-адрес",
            "Неучт. кол-во",
            "Дата вывода на проверку",
            "Статус",
            "Проверил (имя)",
            "Username",
            "Дата отметки",
        ]
    )

    rows = await get_verifications_for_export(session)
    for row in rows:
        dept, article, name, k_addr, unacc, shown_date, status, full_name, username, updated = row
        sheet.append(
            [
                dept,
                article,
                name,
                k_addr or "",
                unacc,
                shown_date.strftime("%d.%m.%Y") if shown_date else "",
                STATUS_LABELS.get(status, status),
                full_name,
                f"@{username}" if username else "",
                updated.strftime("%Y-%m-%d %H:%M") if updated else "",
            ]
        )

    workbook.save(file_path)
    return file_path
