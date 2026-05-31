"""
Планировщик задач APScheduler.

Задачи читают расписание из БД (настройки администратора).
"""

from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from store_check_bot.config import settings
from store_check_bot.db.database import async_session
from store_check_bot.repositories.bot_users import get_all_bot_user_ids
from store_check_bot.repositories.products import get_all_stats
from store_check_bot.services.daily_assignment import assign_daily_products, get_today_progress
from store_check_bot.services.runtime_settings import get_runtime_settings
from store_check_bot.utils.formatting import format_daily_summary


_scheduler: AsyncIOScheduler | None = None
_bot: Bot | None = None


def register_scheduler(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Сохранить ссылки для перенастройки задач из меню «Настройки»."""
    global _scheduler, _bot
    _scheduler = scheduler
    _bot = bot


async def job_assign_daily_products() -> None:
    """Задача по расписанию: новые артикулы на день по отделам."""
    async with async_session() as session:
        count = await assign_daily_products(session)
    logger.info(f"Планировщик: назначено {count} артикулов", )


async def job_send_summary(bot: Bot | None = None) -> None:
    """Сводка по отделам всем подписчикам бота."""
    target_bot = bot or _bot
    if target_bot is None:
        return

    today = datetime.now(settings.tz).date()
    async with async_session() as session:
        progress = await get_today_progress(session, on_date=today)
        dept_stats = await get_all_stats(session, settings.departments_count)
        user_ids = await get_all_bot_user_ids(session)

    if not user_ids:
        return

    text = format_daily_summary(today, progress, dept_stats)
    for user_id in user_ids:
        try:
            await target_bot.send_message(user_id, text, parse_mode="HTML")
        except Exception as exc:
            logger.warning("Не удалось отправить сводку пользователю %s: %s", user_id, exc)


async def apply_scheduler_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Создать или обновить cron-задачи по настройкам из БД."""
    async with async_session() as session:
        runtime = await get_runtime_settings(session)

    scheduler.add_job(
        job_assign_daily_products,
        "cron",
        hour=runtime.daily_assign_hour,
        id="assign_daily_products",
        replace_existing=True,
    )

    for job in scheduler.get_jobs():
        if job.id and job.id.startswith("summary_"):
            scheduler.remove_job(job.id)

    for hour in runtime.summary_hours_list:
        scheduler.add_job(
            job_send_summary,
            "cron",
            hour=hour,
            minute=0,
            args=[bot],
            id=f"summary_{hour}",
            replace_existing=True,
        )

    logger.info(
        f"Планировщик обновлён: назначение в {runtime.daily_assign_hour}, сводки в {runtime.summary_hours}")


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Создать планировщик и зарегистрировать задачи (без start)."""
    scheduler = AsyncIOScheduler(timezone=settings.tz)
    register_scheduler(scheduler, bot)
    return scheduler


async def reschedule_scheduler(bot: Bot) -> None:
    """Перенастроить cron после изменения настроек в боте."""
    if _scheduler is None:
        return
    await apply_scheduler_jobs(_scheduler, bot)
