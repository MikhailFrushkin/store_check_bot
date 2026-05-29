"""Тесты планировщика: сводки в 10/12/14/16 и задача в 06:00."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from store_check_bot.config import settings
from store_check_bot.services.excel_import import import_products_to_db, parse_products_from_excel


@pytest.mark.asyncio
async def test_setup_scheduler_registers_cron_jobs(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Планировщик содержит задачу назначения и сводки в заданные часы."""
    bot = MagicMock()
    from store_check_bot.services import scheduler as scheduler_module
    from store_check_bot.services.scheduler import apply_scheduler_jobs, setup_scheduler

    def _fake_session() -> object:
        class _Ctx:
            async def __aenter__(self) -> object:
                return db_session

            async def __aexit__(self, *args: object) -> None:
                pass

        return _Ctx()

    monkeypatch.setattr(scheduler_module, "async_session", _fake_session)

    scheduler = setup_scheduler(bot)
    await apply_scheduler_jobs(scheduler, bot)
    job_ids = {job.id for job in scheduler.get_jobs()}

    assert "assign_daily_products" in job_ids
    for hour in settings.summary_hours_list:
        assert f"summary_{hour}" in job_ids

    assign_job = scheduler.get_job("assign_daily_products")
    assert assign_job is not None
    assign_trigger = str(assign_job.trigger)
    assert str(settings.daily_assign_hour) in assign_trigger

    summary_job = scheduler.get_job(f"summary_{settings.summary_hours_list[0]}")
    assert summary_job is not None
    assert str(settings.summary_hours_list[0]) in str(summary_job.trigger)


@pytest.mark.asyncio
async def test_job_send_summary_notifies_all_bot_users(
    db_session,
    sample_excel_path,
    day_monday: date,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сводка отправляется всем, кто зарегистрирован через /start."""
    from store_check_bot.services import scheduler as scheduler_module
    from store_check_bot.services.daily_assignment import assign_daily_products

    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)
    await assign_daily_products(db_session, on_date=day_monday, department=1)

    bot = AsyncMock()
    sent_to: list[int] = []

    async def _capture_send(user_id: int, text: str, **kwargs) -> MagicMock:
        sent_to.append(user_id)
        return MagicMock()

    bot.send_message.side_effect = _capture_send

    class _Ctx:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(scheduler_module, "async_session", lambda: _Ctx())
    monkeypatch.setattr(
        scheduler_module,
        "datetime",
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

    await scheduler_module.job_send_summary(bot)

    assert sorted(sent_to) == [111, 222]
    assert bot.send_message.await_count == 2
    texts = [
        call.kwargs.get("text") or (call.args[1] if len(call.args) > 1 else "")
        for call in bot.send_message.await_args_list
    ]
    assert any("Сводка" in t for t in texts)


@pytest.mark.asyncio
async def test_job_send_summary_skips_when_no_users(
    db_session,
    sample_excel_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без подписчиков рассылка не выполняется."""
    from sqlalchemy import delete

    from store_check_bot.db.models import BotUser
    from store_check_bot.services import scheduler as scheduler_module

    await db_session.execute(delete(BotUser))
    await db_session.commit()

    bot = AsyncMock()

    class _Ctx:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(scheduler_module, "async_session", lambda: _Ctx())

    await scheduler_module.job_send_summary(bot)

    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_summary_text_contains_progress(
    db_session,
    sample_excel_path,
    day_monday: date,
) -> None:
    """Текст сводки отражает число назначенных артикулов."""
    from store_check_bot.repositories.products import get_all_stats
    from store_check_bot.services.daily_assignment import assign_daily_products, get_today_progress
    from store_check_bot.utils.formatting import format_daily_summary

    products = parse_products_from_excel(sample_excel_path)
    await import_products_to_db(db_session, products)
    await assign_daily_products(db_session, on_date=day_monday, department=1)

    progress = await get_today_progress(db_session, on_date=day_monday)
    dept_stats = await get_all_stats(db_session, 15)
    text = format_daily_summary(day_monday, progress, dept_stats)

    assert "Сводка" in text
    assert "По отделам" in text
    assert "Отдел 1" in text
    assert str(progress["total"]) in text
