"""
Точка входа: бот проверки неучтённого товара + планировщик задач.
"""

import asyncio
import logging
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from store_check_bot.config import settings
from store_check_bot.db.database import async_session, init_db
from store_check_bot.handlers import router
from store_check_bot.services.daily_assignment import assign_daily_products
from store_check_bot.services.scheduler import apply_scheduler_jobs, setup_scheduler

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """
    Инициализация при старте.

    - Таблицы и миграции SQLite.
    - Если уже после 06:00 и на сегодня нет назначений — назначить артикулы.
    - Запуск APScheduler (06:00 и сводки 10/12/14/16).
    """
    await init_db()

    from store_check_bot.services.runtime_settings import get_runtime_settings

    async with async_session() as session:
        runtime = await get_runtime_settings(session)
        now = datetime.now(settings.tz)
        if now.hour >= runtime.daily_assign_hour:
            assigned = await assign_daily_products(session)
            if assigned:
                logger.info("При старте назначено артикулов: %s", assigned)

    scheduler = setup_scheduler(bot)
    await apply_scheduler_jobs(scheduler, bot)
    scheduler.start()


async def main() -> None:
    """Запуск polling."""
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    async def _startup() -> None:
        await on_startup(bot)

    dp.startup.register(_startup)

    logger.info("Бот неучтённого товара запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
