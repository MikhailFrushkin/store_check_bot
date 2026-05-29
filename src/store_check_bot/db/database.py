"""
Подключение к SQLite и фабрика асинхронных сессий SQLAlchemy.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from store_check_bot.config import settings
from store_check_bot.db.migrate import run_migrations
from store_check_bot.db.models import Base

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Создать таблицы и применить лёгкие миграции."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await run_migrations(engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Контекст сессии для dependency injection."""
    async with async_session() as session:
        yield session
