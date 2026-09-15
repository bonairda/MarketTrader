"""Configuración de la base de datos (SQLAlchemy async) y creación de esquema.

Solo se persisten velas cerradas (PriceBar). Los ticks NO se guardan aquí:
viven en Redis. La tabla de velas se convierte en hypertable de TimescaleDB.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=5)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


# DDL mínima para el MVP. En producción se movería a migraciones (Alembic).
_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS assets (
        id           TEXT PRIMARY KEY,
        symbol       TEXT NOT NULL,
        name         TEXT NOT NULL,
        type         TEXT NOT NULL,
        quote_currency TEXT NOT NULL DEFAULT 'USD',
        is_active    BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_bars (
        asset_id   TEXT NOT NULL,
        interval   TEXT NOT NULL,
        open_time  TIMESTAMPTZ NOT NULL,
        open       DOUBLE PRECISION NOT NULL,
        high       DOUBLE PRECISION NOT NULL,
        low        DOUBLE PRECISION NOT NULL,
        close      DOUBLE PRECISION NOT NULL,
        volume     DOUBLE PRECISION,
        PRIMARY KEY (asset_id, interval, open_time)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist_items (
        asset_id  TEXT PRIMARY KEY,
        added_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        notes     TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alert_rules (
        id          TEXT PRIMARY KEY,
        asset_id    TEXT NOT NULL,
        type        TEXT NOT NULL,
        threshold   DOUBLE PRECISION,
        channels    TEXT NOT NULL DEFAULT 'PUSH',
        enabled     BOOLEAN NOT NULL DEFAULT TRUE,
        last_triggered_at TIMESTAMPTZ
    )
    """,
]


async def init_db() -> None:
    """Crea el esquema mínimo e intenta convertir price_bars en hypertable."""
    async with engine.begin() as conn:
        for stmt in _SCHEMA_STATEMENTS:
            await conn.execute(text(stmt))
        # Convertir en hypertable si la extensión TimescaleDB está disponible.
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            await conn.execute(
                text(
                    "SELECT create_hypertable('price_bars', 'open_time', "
                    "if_not_exists => TRUE, migrate_data => TRUE)"
                )
            )
        except Exception:
            # Si no es TimescaleDB (p. ej. Postgres normal), seguimos con tabla normal.
            pass
