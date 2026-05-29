"""
Настройки приложения в БД.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from store_check_bot.db.models import AppSettings


async def get_app_settings(session: AsyncSession) -> AppSettings:
    """Получить или создать строку настроек id=1."""
    row = await session.get(AppSettings, 1)
    if row is None:
        row = AppSettings(id=1)
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row
