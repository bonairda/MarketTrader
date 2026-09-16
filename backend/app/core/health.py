"""Comprobaciones de salud de las dependencias (BD y Redis)."""

from __future__ import annotations

from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.core.worker_health import worker_is_healthy

log = get_logger("health")


async def check_database() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.warning("[HEALTH] Base de datos no disponible: %s", exc)
        return False


async def check_redis() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception as exc:
        log.warning("[HEALTH] Redis no disponible: %s", exc)
        return False


async def health_report(*, include_worker: bool = False) -> dict:
    db_ok = await check_database()
    redis_ok = await check_redis()
    checks = {"database": db_ok, "redis": redis_ok}
    if include_worker:
        try:
            checks["worker"] = await worker_is_healthy()
        except Exception as exc:
            log.warning("[HEALTH] Heartbeat del worker no disponible: %s", exc)
            checks["worker"] = False
    return {
        "status": "ok" if all(checks.values()) else "degraded",
        "revision": settings.app_revision,
        "checks": checks,
    }
