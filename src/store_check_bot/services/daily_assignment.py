"""
Назначение артикулов на проверку: 10 штук в день на отдел без повторов до новой загрузки.
"""

import logging
from datetime import date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from store_check_bot.config import settings
from store_check_bot.db.models import DailyAssignment, Product, Verification, VerificationStatus
from store_check_bot.services.runtime_settings import get_runtime_settings

logger = logging.getLogger(__name__)


async def get_today_products(
    session: AsyncSession,
    department: int,
    on_date: date | None = None,
) -> list[Product]:
    """
    Товары, назначенные на проверку в указанный день и отдел.

    Args:
        session: Сессия БД.
        department: Номер отдела.
        on_date: Календарная дата (по умолчанию — сегодня в TZ настроек).

    Returns:
        До 10 товаров с join по daily_assignments.
    """
    if on_date is None:
        on_date = datetime.now(settings.tz).date()

    result = await session.execute(
        select(Product)
        .join(DailyAssignment, DailyAssignment.product_id == Product.id)
        .where(
            DailyAssignment.assignment_date == on_date,
            DailyAssignment.department == department,
        )
        .order_by(Product.id)
    )
    return list(result.scalars().all())


async def assign_daily_products(
    session: AsyncSession,
    on_date: date | None = None,
    department: int | None = None,
) -> int:
    """
    Назначить до 10 новых артикулов на день по каждому отделу (или одному).

    Берутся товары отдела, ещё не попадавшие в daily_assignments с момента последней загрузки.

    Returns:
        Число новых назначений.
    """
    if on_date is None:
        on_date = datetime.now(settings.tz).date()

    runtime = await get_runtime_settings(session)
    departments = [department] if department else range(1, settings.departments_count + 1)
    total_assigned = 0

    for dept in departments:
        existing = await session.scalar(
            select(func.count())
            .select_from(DailyAssignment)
            .where(
                DailyAssignment.assignment_date == on_date,
                DailyAssignment.department == dept,
            )
        )
        if existing and existing >= runtime.products_per_day:
            continue

        slots = runtime.products_per_day - (existing or 0)

        already_assigned = select(DailyAssignment.product_id)
        result = await session.execute(
            select(Product)
            .where(
                Product.department == dept,
                Product.id.not_in(already_assigned),
            )
            .order_by(Product.id)
            .limit(slots)
        )
        candidates = list(result.scalars().all())

        for product in candidates:
            session.add(
                DailyAssignment(
                    assignment_date=on_date,
                    department=dept,
                    product_id=product.id,
                )
            )
            product.shown_for_check_date = on_date
            total_assigned += 1

    if total_assigned:
        await session.commit()
        logger.info("Назначено артикулов на %s: %s", on_date, total_assigned)
    return total_assigned


async def all_today_processed(
    session: AsyncSession,
    department: int,
    on_date: date | None = None,
) -> bool:
    """
    Все ли артикулы дня по отделу отмечены как «Отработан».

    Считается по любому пользователю (достаточно одной отметки processed на товар).
    """
    if on_date is None:
        on_date = datetime.now(settings.tz).date()

    products = await get_today_products(session, department, on_date)
    if not products:
        return False

    product_ids = [p.id for p in products]
    result = await session.execute(
        select(func.count(func.distinct(Verification.product_id)))
        .where(
            Verification.product_id.in_(product_ids),
            Verification.status == VerificationStatus.PROCESSED.value,
        )
    )
    processed_count = result.scalar() or 0
    return processed_count >= len(product_ids)


async def get_today_progress(
    session: AsyncSession,
    department: int | None = None,
    on_date: date | None = None,
) -> dict[str, int]:
    """
    Прогресс за день: всего назначено, отработано, не отработано, без отметки.

    department=None — по всем отделам.
    """
    if on_date is None:
        on_date = datetime.now(settings.tz).date()

    query = (
        select(Product.id)
        .join(DailyAssignment, DailyAssignment.product_id == Product.id)
        .where(DailyAssignment.assignment_date == on_date)
    )
    if department is not None:
        query = query.where(DailyAssignment.department == department)

    result = await session.execute(query)
    product_ids = [row[0] for row in result.all()]
    total = len(product_ids)
    if total == 0:
        return {"total": 0, "processed": 0, "not_processed": 0, "pending": 0}

    proc_result = await session.scalar(
        select(func.count(func.distinct(Verification.product_id)))
        .where(
            Verification.product_id.in_(product_ids),
            Verification.status == VerificationStatus.PROCESSED.value,
        )
    )
    not_proc_result = await session.scalar(
        select(func.count(func.distinct(Verification.product_id)))
        .where(
            Verification.product_id.in_(product_ids),
            Verification.status == VerificationStatus.NOT_PROCESSED.value,
        )
    )
    processed = proc_result or 0
    not_processed = not_proc_result or 0
    marked = await session.scalar(
        select(func.count(func.distinct(Verification.product_id))).where(
            Verification.product_id.in_(product_ids)
        )
    )
    pending = total - (marked or 0)

    return {
        "total": total,
        "processed": processed,
        "not_processed": not_processed,
        "pending": max(pending, 0),
    }
