"""
ORM-модели: неучтённый товар, проверки, назначения на день, подписчики бота.
"""

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех таблиц."""


class VerificationStatus(str, Enum):
    """Результат отработки артикула."""

    PROCESSED = "processed"  # отработан
    NOT_PROCESSED = "not_processed"  # не отработан


class Product(Base):
    """
    Неучтённый товар из еженедельной выгрузки Excel.

    Поля соответствуют колонкам файла «Неучтенные товары.xlsx».
    shown_for_check_date — дата, когда артикул попал в дневную десятку на проверку.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop: Mapped[int | None] = mapped_column(Integer, nullable=True)
    department: Mapped[int] = mapped_column(Integer, index=True)
    subdepartment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    article: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(500))
    loc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gamma: Mapped[str | None] = mapped_column(String(32), nullable=True)
    top: Mapped[int | None] = mapped_column(Integer, nullable=True)
    theoretical_stock: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_ls: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_sscc: Mapped[float | None] = mapped_column(Float, nullable=True)
    qty_z_address: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_rm: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_em: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_rd: Mapped[float | None] = mapped_column(Float, nullable=True)
    warehouse_buffer: Mapped[float | None] = mapped_column(Float, nullable=True)
    unaccounted_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    k_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    z_address: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_movement: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    shown_for_check_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    verifications: Mapped[list["Verification"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    daily_assignments: Mapped[list["DailyAssignment"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class Verification(Base):
    """Отметка сотрудника: отработан / не отработан (одна запись на пару товар + пользователь)."""

    __tablename__ = "verifications"
    __table_args__ = (UniqueConstraint("product_id", "user_id", name="uq_product_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    product: Mapped["Product"] = relationship(back_populates="verifications")


class DailyAssignment(Base):
    """Какие артикулы назначены на проверку в конкретный день и отдел (до 10 шт.)."""

    __tablename__ = "daily_assignments"
    __table_args__ = (
        UniqueConstraint("assignment_date", "department", "product_id", name="uq_day_dept_product"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_date: Mapped[date] = mapped_column(Date, index=True)
    department: Mapped[int] = mapped_column(Integer, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))

    product: Mapped["Product"] = relationship(back_populates="daily_assignments")


class BotUser(Base):
    """Пользователи, нажавшие /start — для рассылки сводок."""

    __tablename__ = "bot_users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    """
    Настройки бота (одна строка id=1).

    NULL в полях расписания — использовать значения по умолчанию из .env.
    """

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    last_excel_upload_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    daily_assign_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_hours: Mapped[str | None] = mapped_column(String(64), nullable=True)
    products_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
