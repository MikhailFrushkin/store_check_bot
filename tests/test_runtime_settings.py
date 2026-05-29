"""Тесты настроек из БД и форматирования сводки по отделам."""

from datetime import date

import pytest

from store_check_bot.services.runtime_settings import (
    get_runtime_settings,
    save_runtime_settings,
    validate_summary_hours,
)
from store_check_bot.utils.formatting import format_daily_summary, _department_summary_line


def test_validate_summary_hours() -> None:
    """Парсинг часов сводки."""
    assert validate_summary_hours("10, 12, 14") == [10, 12, 14]


@pytest.mark.asyncio
async def test_save_runtime_settings(db_session) -> None:
    """Сохранение настроек в app_settings."""
    runtime = await save_runtime_settings(
        db_session,
        daily_assign_hour=7,
        summary_hours="9,15",
        products_per_day=12,
    )
    assert runtime.daily_assign_hour == 7
    assert runtime.summary_hours_list == [9, 15]
    assert runtime.products_per_day == 12

    again = await get_runtime_settings(db_session)
    assert again.daily_assign_hour == 7


def test_department_summary_line_done() -> None:
    """Отдел полностью отработан."""
    line = _department_summary_line(
        {"department": 3, "total": 10, "present": 10, "absent": 0, "unchecked": 0}
    )
    assert "отработан" in line
    assert "Отдел 3" in line


def test_format_daily_summary_with_departments() -> None:
    """Сводка содержит блок по отделам."""
    text = format_daily_summary(
        date(2026, 5, 29),
        {"total": 20, "processed": 5, "not_processed": 2, "pending": 13},
        [
            {"department": 1, "total": 10, "present": 10, "absent": 0, "unchecked": 0},
            {"department": 2, "total": 10, "present": 0, "absent": 0, "unchecked": 10},
        ],
    )
    assert "По отделам" in text
    assert "отработан" in text
    assert "ещё не начат" in text
