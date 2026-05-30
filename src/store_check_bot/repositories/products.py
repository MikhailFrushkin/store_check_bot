"""
Запросы к БД: проверки и выгрузка для Excel.
"""
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from store_check_bot.db.models import DailyAssignment, Product, Verification, VerificationStatus


async def get_product(session: AsyncSession, product_id: int) -> Product | None:
    """Найти товар по id."""
    return await session.get(Product, product_id)


async def get_user_verification(
    session: AsyncSession,
    product_id: int,
    user_id: int,
) -> Verification | None:
    """Отметка конкретного пользователя по товару."""
    result = await session.execute(
        select(Verification).where(
            Verification.product_id == product_id,
            Verification.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert_verification(
    session: AsyncSession,
    product_id: int,
    user_id: int,
    username: str | None,
    full_name: str,
    status: VerificationStatus,
) -> Verification:
    """Создать или обновить отметку отработки."""
    stmt = sqlite_insert(Verification).values(
        product_id=product_id,
        user_id=user_id,
        username=username,
        full_name=full_name,
        status=status.value,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["product_id", "user_id"],
        set_={
            "username": username,
            "full_name": full_name,
            "status": status.value,
        },
    )
    await session.execute(stmt)
    await session.commit()
    result = await session.execute(
        select(Verification).where(
            Verification.product_id == product_id,
            Verification.user_id == user_id,
        )
    )
    return result.scalar_one()


async def get_department_stats(session: AsyncSession, department: int) -> dict[str, int]:
    """Сводка по отделу за сегодня (назначенные артикулы)."""
    from datetime import datetime

    from store_check_bot.config import settings
    from store_check_bot.services.daily_assignment import get_today_progress

    today = datetime.now(settings.tz).date()
    progress = await get_today_progress(session, department, today)
    return {
        "department": department,
        "total": progress["total"],
        "checked": progress["processed"] + progress["not_processed"],
        "present": progress["processed"],
        "absent": progress["not_processed"],
        "unchecked": progress["pending"],
    }  # present/absent — для совместимости с format_stats_message


async def get_all_stats(session: AsyncSession, departments_count: int) -> list[dict[str, int]]:
    """Статистика по всем отделам за сегодня."""
    stats = []
    for dept in range(1, departments_count + 1):
        stats.append(await get_department_stats(session, dept))
    return stats


async def get_verifications_for_export(session: AsyncSession) -> list[tuple]:
    """Строки для Excel: товар + отметка + дата вывода на проверку.

    Возвращает только товары, которые были показаны на проверку.
    """
    result = await session.execute(
        select(
            Product.department,
            Product.article,
            Product.name,
            Product.k_address,
            Product.unaccounted_qty,
            Product.shown_for_check_date,
            Verification.status,
            Verification.full_name,
            Verification.username,
            Verification.updated_at,
        )
        .outerjoin(Verification, Verification.product_id == Product.id)
        .where(Product.shown_for_check_date.is_not(None))  # Только показанные товары
        .order_by(Product.department, Product.article)
    )
    return list(result.all())