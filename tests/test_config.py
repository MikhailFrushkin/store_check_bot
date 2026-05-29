"""Tests for settings parsing."""

from store_check_bot.config import Settings


def test_parse_admin_user_ids_from_string() -> None:
    """Parse comma-separated IDs."""
    settings = Settings(bot_token="test", admin_user_ids="111, 222,333")
    assert settings.admin_user_ids == [111, 222, 333]


def test_user_has_full_access() -> None:
    """Check membership in admin list."""
    settings = Settings(bot_token="test", admin_user_ids=[42])
    assert settings.user_has_full_access(42) is True
    assert settings.user_has_full_access(1) is False
