"""Configuración de la base de datos (SQLAlchemy async).

El esquema se gestiona con Alembic (carpeta `alembic/`), NO con DDL a mano.
Solo se persisten velas cerradas (PriceBar); los ticks viven en Redis.
Para aplicar migraciones: `alembic upgrade head` (lo hacen los contenedores al
arrancar, ver docker-compose.yml).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=5)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
