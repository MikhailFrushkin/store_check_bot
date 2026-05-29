"""Тесты назначения артикулов в 06:00 и смены десятки по дням."""

from datetime import date

import pytest
from sqlalchemy import func, select

from store_check_bot.config import settings
from store_check_bot.db.models import DailyAssignment, Product
from store_check_bot.services.daily_assignment import assign_daily_products, get_today_products
from store_check_bot.services.excel_import import import_products_to_db, parse_products_from_excel


@pytest.mark.asyncio
async def test_assign_daily_products_ten_per_department(
    db_session,
    sample_excel_path,
    day_monday: date,
) -> None:
    """В понедельник назначается ровно 10 артикулов на отдел 1."""
    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)

    assigned = await assign_daily_products(db_session, on_date=day_monday, department=1)

    assert assigned == settings.products_per_day
    today = await get_today_products(db_session, department=1, on_date=day_monday)
    assert len(today) == 10


@pytest.mark.asyncio
async def test_assign_sets_shown_for_check_date(
    db_session,
    sample_excel_path,
    day_monday: date,
) -> None:
    """У назначенных артикулов проставляется дата вывода на проверку."""
    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)
    await assign_daily_products(db_session, on_date=day_monday, department=1)

    today = await get_today_products(db_session, department=1, on_date=day_monday)
    assert all(p.shown_for_check_date == day_monday for p in today)


@pytest.mark.asyncio
async def test_tuesday_gets_different_articles(
    db_session,
    sample_excel_path,
    day_monday: date,
    day_tuesday: date,
) -> None:
    """Во вторник — другие 10 артикулов, без повторов с понедельником."""
    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)

    await assign_daily_products(db_session, on_date=day_monday, department=1)
    monday = await get_today_products(db_session, department=1, on_date=day_monday)
    monday_ids = {p.id for p in monday}

    assigned_tue = await assign_daily_products(db_session, on_date=day_tuesday, department=1)
    assert assigned_tue == settings.products_per_day

    tuesday = await get_today_products(db_session, department=1, on_date=day_tuesday)
    tuesday_ids = {p.id for p in tuesday}

    assert monday_ids.isdisjoint(tuesday_ids)


@pytest.mark.asyncio
async def test_job_assign_daily_products_like_scheduler_6am(
    db_session,
    sample_excel_path,
    day_monday: date,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Задача планировщика в 06:00 (job_assign_daily_products) назначает артикулы."""
    from store_check_bot.services import scheduler as scheduler_module

    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)

    def _fake_session() -> object:
        class _Ctx:
            async def __aenter__(self) -> object:
                return db_session

            async def __aexit__(self, *args: object) -> None:
                pass

        return _Ctx()

    monkeypatch.setattr(scheduler_module, "async_session", _fake_session)
    monkeypatch.setattr(
        "store_check_bot.services.daily_assignment.datetime",
        type(
            "DT",
            (),
            {
                "now": staticmethod(
                    lambda tz=None: type(
                        "N",
                        (),
                        {"date": staticmethod(lambda: day_monday)},
                    )()
                ),
            },
        ),
    )

    await scheduler_module.job_assign_daily_products()

    count = await db_session.scalar(
        select(func.count())
        .select_from(DailyAssignment)
        .where(DailyAssignment.assignment_date == day_monday)
    )
    # отдел 1: 10 арт., отдел 2: 5 арт. (в файле только 5 товаров)
    assert count == 15


@pytest.mark.asyncio
async def test_new_upload_resets_assignment_queue(
    db_session,
    sample_excel_path,
    day_monday: date,
    day_tuesday: date,
) -> None:
    """После новой загрузки файла очередь показа сбрасывается."""
    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)
    await assign_daily_products(db_session, on_date=day_monday, department=1)

    await import_products_to_db(db_session, products)
    assigned = await assign_daily_products(db_session, on_date=day_tuesday, department=1)

    assert assigned == settings.products_per_day
    tuesday = await get_today_products(db_session, department=1, on_date=day_tuesday)
    assert len(tuesday) == 10
