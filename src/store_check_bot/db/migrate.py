"""
Миграция SQLite без Alembic: новые колонки и удаление устаревших.

Старая схема имела barcode, address, image_url (NOT NULL) — они удаляются,
чтобы не ломать вставку по новой модели с полем article.
"""

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine


# (таблица, колонка, SQL тип)
NEW_COLUMNS: list[tuple[str, str, str]] = [
    ("products", "shop", "INTEGER"),
    ("products", "subdepartment", "INTEGER"),
    ("products", "article", "VARCHAR(64)"),
    ("products", "loc", "VARCHAR(64)"),
    ("products", "gamma", "VARCHAR(32)"),
    ("products", "top", "INTEGER"),
    ("products", "theoretical_stock", "FLOAT"),
    ("products", "capacity", "FLOAT"),
    ("products", "on_ls", "FLOAT"),
    ("products", "on_sscc", "FLOAT"),
    ("products", "qty_z_address", "FLOAT"),
    ("products", "on_rm", "FLOAT"),
    ("products", "on_em", "FLOAT"),
    ("products", "on_rd", "FLOAT"),
    ("products", "warehouse_buffer", "FLOAT"),
    ("products", "unaccounted_qty", "FLOAT"),
    ("products", "k_address", "VARCHAR(128)"),
    ("products", "z_address", "VARCHAR(128)"),
    ("products", "last_movement", "DATETIME"),
    ("products", "shown_for_check_date", "DATE"),
    ("app_settings", "daily_assign_hour", "INTEGER"),
    ("app_settings", "summary_hours", "VARCHAR(64)"),
    ("app_settings", "products_per_day", "INTEGER"),
]


async def run_migrations(engine: AsyncEngine) -> None:
    """Добавить новые колонки и убрать устаревшие в products."""
    async with engine.begin() as conn:
        def _migrate(sync_conn) -> None:
            inspector = inspect(sync_conn)
            table_names = inspector.get_table_names()

            for table, column, col_type in NEW_COLUMNS:
                if table not in table_names:
                    continue
                existing_cols = {c["name"] for c in inspector.get_columns(table)}
                if column in existing_cols:
                    continue
                sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                logger.info("Миграция: добавлена колонка %s.%s", table, column)

            if "products" not in table_names:
                return

            existing = {c["name"] for c in inspector.get_columns("products")}

            # Перенос штрихкода в артикул перед удалением barcode
            if "barcode" in existing and "article" in existing:
                sync_conn.execute(
                    text(
                        "UPDATE products SET article = CAST(barcode AS TEXT) "
                        "WHERE article IS NULL OR article = ''"
                    )
                )


        await conn.run_sync(_migrate)
