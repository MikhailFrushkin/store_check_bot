"""
Подписчики бота (кто нажал /start) — для рассылки сводок.
"""

from aiogram.types import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from store_check_bot.db.models import BotUser


async def register_bot_user(session: AsyncSession, user: User) -> None:
    """Добавить или обновить пользователя в списке рассылки."""
    row = await session.get(BotUser, user.id)
    full_name = user.full_name or user.username or str(user.id)
    if row is None:
        session.add(
            BotUser(
                user_id=user.id,
                username=user.username,
                full_name=full_name,
            )
        )
    else:
        row.username = user.username
        row.full_name = full_name
    await session.commit()


async def get_all_bot_user_ids(session: AsyncSession) -> list[int]:
    """Telegram ID всех подписчиков."""
    result = await session.execute(select(BotUser.user_id))
    return [row[0] for row in result.all()]
