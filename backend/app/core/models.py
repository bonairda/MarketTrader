"""Modelos declarativos de SQLAlchemy.

Definen el esquema de la base de datos. Alembic los usa para autogenerar
migraciones. Solo se persisten velas (PriceBar); los ticks viven en Redis.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """Usuario de la aplicación. El `role` controla los permisos (OWNER/VIEWER)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="OWNER")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    quote_currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PriceBar(Base):
    __tablename__ = "price_bars"

    asset_id: Mapped[str] = mapped_column(String, primary_key=True)
    interval: Mapped[str] = mapped_column(String, primary_key=True)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    # Clave compuesta: cada usuario tiene su propia watchlist; dos usuarios
    # pueden seguir el mismo activo de forma independiente.
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    asset_id: Mapped[str] = mapped_column(String, primary_key=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    asset_id: Mapped[str] = mapped_column(String, nullable=False)
    # PRICE_CROSS | PERCENT_CHANGE | INDICATOR_CROSS
    type: Mapped[str] = mapped_column(String, nullable=False, default="PRICE_CROSS")
    direction: Mapped[str] = mapped_column(String, nullable=False, default="ABOVE")
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    # Indicador a vigilar en INDICATOR_CROSS (p. ej. "rsi14"). Nulo en otros tipos.
    indicator: Mapped[str | None] = mapped_column(String, nullable=True)
    # Intervalo de velas usado por PERCENT_CHANGE / INDICATOR_CROSS.
    timeframe: Mapped[str] = mapped_column(String, nullable=False, default="1m")
    channels: Mapped[str] = mapped_column(String, nullable=False, default="TELEGRAM")
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Position(Base):
    """Posición de cartera simulada (introducida manualmente por el usuario)."""

    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    asset_id: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Operation(Base):
    """Operación de inversión fiscal, expresada en divisa original y EUR.

    `fx_rate_to_eur` significa EUR recibidos por una unidad de la divisa
    original (por ejemplo, 1 USD = 0.92 EUR). Los importes monetarios usan
    Decimal/NUMERIC para evitar errores binarios de redondeo.
    """

    __tablename__ = "operations"
    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_operations_side"),
        CheckConstraint("quantity > 0", name="ck_operations_quantity_positive"),
        CheckConstraint(
            "unit_price_original > 0", name="ck_operations_unit_price_positive"
        ),
        CheckConstraint(
            "gross_amount_original > 0", name="ck_operations_gross_positive"
        ),
        CheckConstraint("fees_original >= 0", name="ck_operations_fees_nonnegative"),
        CheckConstraint(
            "fees_original <= gross_amount_original",
            name="ck_operations_fees_not_above_gross",
        ),
        CheckConstraint("fx_rate_to_eur > 0", name="ck_operations_fx_positive"),
        Index(
            "ix_operations_user_asset_order",
            "user_id",
            "asset_id",
            "trade_date",
            "executed_at",
            "id",
        ),
        Index("ix_operations_user_trade_date", "user_id", "trade_date"),
        Index(
            "ux_operations_user_source_external_id",
            "user_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    asset_id: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    unit_price_original: Mapped[Decimal] = mapped_column(
        Numeric(30, 12), nullable=False
    )
    gross_amount_original: Mapped[Decimal] = mapped_column(
        Numeric(30, 12), nullable=False
    )
    fees_original: Mapped[Decimal] = mapped_column(
        Numeric(30, 12), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(12), nullable=False)
    fx_rate_to_eur: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    fx_source: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="MANUAL")
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OperationAuditLog(Base):
    """Registro inmutable de altas y bajas del libro fiscal."""

    __tablename__ = "operation_audit_log"
    __table_args__ = (
        CheckConstraint("action IN ('CREATE', 'DELETE')", name="ck_operation_audit_action"),
        Index("ix_operation_audit_user_operation", "user_id", "operation_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    operation_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CorporateEvent(Base):
    """Evento corporativo del usuario: dividendo (con retención) o split.

    - DIVIDEND: `gross_amount_original`/`withholding_original` en `currency`,
      con `fx_rate_to_eur` para el cálculo en EUR. `quantity`/`ratio` no aplican.
    - SPLIT: `ratio` = nuevas acciones por cada antigua (2 = 2:1; 0.5 = 1:2).
    """

    __tablename__ = "corporate_events"
    __table_args__ = (
        CheckConstraint(
            "type IN ('DIVIDEND', 'SPLIT')", name="ck_corporate_events_type"
        ),
        Index(
            "ix_corporate_events_user_asset_date",
            "user_id",
            "asset_id",
            "event_date",
        ),
        Index(
            "ux_corporate_events_user_external_id",
            "user_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    asset_id: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Dividendos
    gross_amount_original: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    withholding_original: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    currency: Mapped[str | None] = mapped_column(String(12))
    fx_rate_to_eur: Mapped[Decimal | None] = mapped_column(Numeric(24, 12))
    # Splits
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(24, 12))
    fx_source: Mapped[str | None] = mapped_column(String, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
