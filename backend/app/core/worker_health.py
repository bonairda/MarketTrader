"""Heartbeat compartido del worker para healthchecks de Docker/Coolify."""

from __future__ import annotations

import time

from app.core.config import settings
from app.core.redis_client import get_redis

WORKER_HEARTBEAT_KEY = "worker:heartbeat"


async def write_worker_heartbeat() -> None:
    await get_redis().set(
        WORKER_HEARTBEAT_KEY,
        str(time.time()),
        ex=settings.worker_heartbeat_ttl_seconds,
    )


async def worker_is_healthy() -> bool:
    value = await get_redis().get(WORKER_HEARTBEAT_KEY)
    if not value:
        return False
    try:
        age = time.time() - float(value)
    except (TypeError, ValueError):
        return False
    return age <= settings.worker_heartbeat_ttl_seconds
