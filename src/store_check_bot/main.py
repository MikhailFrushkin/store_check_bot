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
from loguru import logger

from store_check_bot.config import settings
from store_check_bot.db.database import async_session, init_db
from store_check_bot.handlers import router
from store_check_bot.services.daily_assignment import assign_daily_products
from store_check_bot.services.scheduler import apply_scheduler_jobs, setup_scheduler


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
                logger.info(f"При старте назначено артикулов: {assigned}")

    scheduler = setup_scheduler(bot)
    await apply_scheduler_jobs(scheduler, bot)
    scheduler.start()


async def main() -> None:
    """Запуск polling."""
    logger.remove()

    # Добавляем вывод в консоль с цветами и форматированием
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True
    )

    # Добавляем вывод в файл с ротацией
    logger.add(
        "logs/app.log",
        rotation="10 MB",  # Ротация при достижении 10 MB
        retention="7 days",  # Хранить 7 дней
        compression="zip",  # Сжимать старые логи
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
        encoding="utf-8"
    )

    # Отдельный файл для ошибок
    logger.add(
        "logs/errors.log",
        level="ERROR",
        rotation="100 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
        backtrace=True,  # Показывать полный traceback
        diagnose=True  # Показывать переменные при ошибке
    )

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
