"""Тесты загрузки Excel в базу данных."""

from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select

from store_check_bot.db.models import AppSettings, DailyAssignment, Product, Verification
from store_check_bot.services.excel_import import import_products_to_db, parse_products_from_excel


@pytest.mark.asyncio
async def test_import_products_to_db_replaces_catalog(
    db_session,
    sample_excel_path: Path,
) -> None:
    """Импорт записывает все строки и сбрасывает старые данные."""
    products = parse_products_from_excel(sample_excel_path)
    assert len(products) == 30

    count = await import_products_to_db(db_session, products)

    assert count == 30
    total = await db_session.scalar(select(func.count()).select_from(Product))
    assert total == 30

    app = await db_session.get(AppSettings, 1)
    assert app is not None
    assert app.last_excel_upload_at is not None


@pytest.mark.asyncio
async def test_import_clears_verifications_and_assignments(
    db_session,
    sample_excel_path: Path,
) -> None:
    """Повторная загрузка удаляет проверки и назначения."""
    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)

    first = (await db_session.execute(select(Product).limit(1))).scalar_one()
    db_session.add(
        Verification(
            product_id=first.id,
            user_id=999,
            full_name="X",
            status="processed",
        )
    )
    db_session.add(
        DailyAssignment(
            assignment_date=datetime(2026, 5, 25).date(),
            department=1,
            product_id=first.id,
        )
    )
    await db_session.commit()

    await import_products_to_db(db_session, products)

    ver_count = await db_session.scalar(select(func.count()).select_from(Verification))
    assign_count = await db_session.scalar(select(func.count()).select_from(DailyAssignment))
    assert ver_count == 0
    assert assign_count == 0


@pytest.mark.asyncio
async def test_import_stores_excel_fields(db_session, sample_excel_path: Path) -> None:
    """Поля артикула и отдела сохраняются корректно."""
    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)

    result = await db_session.execute(
        select(Product).where(Product.name == "Товар отдел 1 номер 1")
    )
    product = result.scalar_one()
    assert product.department == 1
    assert str(product.article).endswith("1")
    assert product.k_address == "K-1"
    assert product.unaccounted_qty == 1
