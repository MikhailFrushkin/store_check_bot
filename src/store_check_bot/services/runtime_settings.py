"""
Рабочие настройки бота: из БД с подстановкой значений по умолчанию из .env.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from store_check_bot.config import settings
from store_check_bot.repositories.settings_repo import get_app_settings


@dataclass(frozen=True)
class RuntimeSettings:
    """Актуальные параметры расписания и лимитов."""

    products_per_day: int
    daily_assign_hour: int
    summary_hours: str
    summary_hours_list: list[int]


def parse_summary_hours(value: str) -> list[int]:
    """Разобрать строку часов «10,12,14,16»."""
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def validate_summary_hours(value: str) -> list[int]:
    """
    Проверить и вернуть список часов 0–23.

    Raises:
        ValueError: Некорректный формат или значение.
    """
    if not value.strip():
        raise ValueError("Укажите хотя бы один час через запятую")
    hours = parse_summary_hours(value)
    for hour in hours:
        if hour < 0 or hour > 23:
            raise ValueError("Час должен быть от 0 до 23")
    return sorted(set(hours))


async def get_runtime_settings(session: AsyncSession) -> RuntimeSettings:
    """Прочитать настройки из app_settings или .env."""
    app = await get_app_settings(session)

    products_per_day = (
        app.products_per_day
        if app.products_per_day is not None
        else settings.products_per_day
    )
    daily_assign_hour = (
        app.daily_assign_hour
        if app.daily_assign_hour is not None
        else settings.daily_assign_hour
    )
    summary_hours = (
        app.summary_hours if app.summary_hours is not None else settings.summary_hours
    )
    hours_list = parse_summary_hours(summary_hours)

    return RuntimeSettings(
        products_per_day=products_per_day,
        daily_assign_hour=daily_assign_hour,
        summary_hours=summary_hours,
        summary_hours_list=hours_list,
    )


async def save_runtime_settings(
    session: AsyncSession,
    *,
    products_per_day: int | None = None,
    daily_assign_hour: int | None = None,
    summary_hours: str | None = None,
) -> RuntimeSettings:
    """Сохранить изменённые настройки в БД."""
    app = await get_app_settings(session)

    if products_per_day is not None:
        if products_per_day < 1 or products_per_day > 100:
            raise ValueError("Количество артикулов должно быть от 1 до 100")
        app.products_per_day = products_per_day

    if daily_assign_hour is not None:
        if daily_assign_hour < 0 or daily_assign_hour > 23:
            raise ValueError("Час обновления должен быть от 0 до 23")
        app.daily_assign_hour = daily_assign_hour

    if summary_hours is not None:
        hours = validate_summary_hours(summary_hours)
        app.summary_hours = ",".join(str(h) for h in hours)

    await session.commit()
    return await get_runtime_settings(session)
