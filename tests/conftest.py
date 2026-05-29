"""Общие фикстуры pytest: БД в памяти и образец Excel."""

from collections.abc import AsyncGenerator
from datetime import date
from pathlib import Path

import pytest
import pytest_asyncio
from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from store_check_bot.config import settings
from store_check_bot.db.models import Base, BotUser

EXCEL_HEADERS = [
    "Магазин",
    "Отдел",
    "Подотдел",
    "Артикул",
    "Наименование",
    "LOC",
    "Гамма",
    "ТОП",
    "Теор. запас",
    "Вместимость",
    "На LS",
    "На SSCC в ТЗ",
    "Кол-во на Z адресе",
    "На RM",
    "НА ЕМ",
    "На RD",
    "Буфер склада",
    "Неучтенный товар",
    "К-Адрес",
    "Z-Адрес",
    "Последнее движение",
]


@pytest.fixture
def anyio_backend() -> str:
    """Бэкенд asyncio для pytest-asyncio."""
    return "asyncio"


@pytest.fixture
def products_per_day(monkeypatch: pytest.MonkeyPatch) -> int:
    """Лимит артикулов в день."""
    monkeypatch.setattr(settings, "products_per_day", 10)
    return 10


@pytest.fixture
def sample_excel_path(tmp_path: Path) -> Path:
    """
    Excel с 25 артикулами в отделе 1 и 5 артикулами в отделе 2.

    Достаточно для проверки смены десяток по дням.
    """
    file_path = tmp_path / "neuchtennye.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(EXCEL_HEADERS)

    for i in range(1, 26):
        sheet.append(
            [
                67,
                1,
                100 + i,
                4600000000000 + i,
                f"Товар отдел 1 номер {i}",
                "LOC1",
                "A0",
                1,
                10,
                10,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                1,
                f"K-{i}",
                None,
                None,
            ]
        )
    for i in range(1, 6):
        sheet.append(
            [
                67,
                2,
                200 + i,
                4700000000000 + i,
                f"Товар отдел 2 номер {i}",
                "LOC2",
                "A0",
                1,
                5,
                5,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                1,
                f"K2-{i}",
                None,
                None,
            ]
        )

    workbook.save(file_path)
    workbook.close()
    return file_path


@pytest_asyncio.fixture
async def db_session(products_per_day: int) -> AsyncGenerator[AsyncSession, None]:
    """Изолированная SQLite в памяти для одного теста."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        session.add(
            BotUser(user_id=111, username="tester", full_name="Тестовый пользователь")
        )
        session.add(BotUser(user_id=222, username="tester2", full_name="Второй"))
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
def day_monday() -> date:
    """Фиксированная дата для сценариев назначения."""
    return date(2026, 5, 25)


@pytest.fixture
def day_tuesday() -> date:
    """Следующий день после понедельника."""
    return date(2026, 5, 26)
