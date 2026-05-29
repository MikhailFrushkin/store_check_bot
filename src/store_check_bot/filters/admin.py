"""
Проверка прав пользователя по списку Telegram ID из .env.

Не используется членство в группе — только явный список ADMIN_USER_IDS.
"""

from aiogram.types import Message, User

from store_check_bot.config import settings


def is_privileged_user(user: User | None) -> bool:
    """
    Есть ли у пользователя полный доступ к функциям бота.

    Args:
        user: Объект пользователя Telegram или None.

    Returns:
        True, если user.id входит в settings.admin_user_ids.
    """
    if user is None:
        return False
    return settings.user_has_full_access(user.id)


def message_from_privileged(message: Message) -> bool:
    """Удобная обёртка для проверки отправителя сообщения."""
    return is_privileged_user(message.from_user)
