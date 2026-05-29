"""
Конфигурация бота проверки неучтённого товара (.env).
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import dotenv_values, load_dotenv
from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]
DB_FILE = PROJECT_ROOT / "store_check.db"

ENV_CANDIDATES = (
    PROJECT_ROOT / ".env",
    PACKAGE_DIR / ".env",
)

# Часовой пояс для планировщика и «сегодня»
DEFAULT_TIMEZONE = ZoneInfo("Europe/Moscow")


def resolve_env_file() -> Path:
    """Найти первый непустой .env."""
    checked: list[str] = []
    for path in ENV_CANDIDATES:
        checked.append(str(path))
        if not path.is_file():
            continue
        if path.stat().st_size == 0:
            continue
        return path
    raise RuntimeError(
        "Файл .env не найден или пуст. Создайте его в одном из мест:\n"
        + "\n".join(f"  • {p}" for p in checked)
        + "\n\nBOT_TOKEN=...\nADMIN_USER_IDS=123456789"
    )


class Settings(BaseSettings):
    """Настройки из окружения."""

    model_config = SettingsConfigDict(extra="ignore")

    bot_token: str
    admin_user_ids: list[int] = []
    products_per_day: int = 10
    daily_assign_hour: int = 6
    summary_hours: str = "10,12,14,16"
    timezone: str = "Europe/Moscow"

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def parse_admin_user_ids(cls, value: object) -> list[int]:
        """Разобрать ADMIN_USER_IDS."""
        if value is None or value == "":
            return []
        if isinstance(value, int):
            return [value]
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, str):
            return [int(part.strip()) for part in value.split(",") if part.strip()]
        raise ValueError("admin_user_ids должен быть списком ID через запятую")

    @property
    def database_url(self) -> str:
        """SQLite в корне проекта."""
        return f"sqlite+aiosqlite:///{DB_FILE.as_posix()}"

    @property
    def departments_count(self) -> int:
        """Количество отделов (кнопки 1–15)."""
        return 15

    @property
    def tz(self) -> ZoneInfo:
        """Часовой пояс планировщика."""
        return ZoneInfo(self.timezone)

    @property
    def summary_hours_list(self) -> list[int]:
        """Часы рассылки сводки: 10, 12, 14, 16."""
        return [int(h.strip()) for h in self.summary_hours.split(",") if h.strip()]

    def user_has_full_access(self, user_id: int) -> bool:
        """Полный доступ: загрузка Excel и отчёты."""
        return user_id in self.admin_user_ids


def load_settings() -> Settings:
    """Загрузить настройки из .env."""
    env_path = resolve_env_file()
    values = dotenv_values(env_path)
    if not values.get("BOT_TOKEN"):
        raise RuntimeError(f"В {env_path} нет BOT_TOKEN.")
    load_dotenv(env_path, override=True)
    os.environ.update({k: v for k, v in values.items() if v is not None})
    try:
        return Settings()
    except ValidationError as exc:
        raise RuntimeError(f"Проверьте {env_path}.") from exc


settings = load_settings()
