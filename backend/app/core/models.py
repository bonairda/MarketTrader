"""Modelos declarativos de SQLAlchemy.

Definen el esquema de la base de datos. Alembic los usa para autogenerar
migraciones. Solo se persisten velas (PriceBar); los ticks viven en Redis.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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

    asset_id: Mapped[str] = mapped_column(String, primary_key=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String, primary_key=True)
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
    asset_id: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
