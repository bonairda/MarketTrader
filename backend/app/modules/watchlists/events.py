"""Eventos de cambio de la watchlist.

Cuando la watchlist cambia (alta/baja de un activo), se publica en este canal
Redis. El worker de ingestión lo escucha para resuscribirse en caliente, sin
necesidad de reiniciarse.
"""

from __future__ import annotations

from app.core.redis_client import get_redis

WATCHLIST_CHANGED_CHANNEL = "watchlist:changed"


async def notify_watchlist_changed() -> None:
    await get_redis().publish(WATCHLIST_CHANGED_CHANNEL, "changed")
