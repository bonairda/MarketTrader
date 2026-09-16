"""Servicio del dashboard: agrega el estado de la watchlist.

Para cada activo de la watchlist toma sus velas recientes y su precio en vivo,
calcula un resumen (cambio %, máx/mín, volatilidad) y deriva top movers y los
más volátiles. El resultado se cachea brevemente en Redis para que la pantalla
de inicio cargue instantánea.
"""

from __future__ import annotations

import json

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.modules.dashboard import metrics
from app.modules.market_data import bars, live
from app.modules.watchlists import repository as watchlist_repo

log = get_logger("dashboard.service")

_CACHE_KEY = "dashboard:payload"
_CACHE_TTL_SECONDS = 10
# Ventana de velas para el cálculo del cambio del día (1m x 1440 = 24h).
_WINDOW_INTERVAL = "1m"
_WINDOW_LIMIT = 1440


async def get_dashboard(use_cache: bool = True) -> dict:
    redis = get_redis()
    if use_cache:
        cached = await redis.get(_CACHE_KEY)
        if cached:
            return json.loads(cached)

    payload = await _build_dashboard()
    await redis.set(_CACHE_KEY, json.dumps(payload), ex=_CACHE_TTL_SECONDS)
    return payload


async def _build_dashboard() -> dict:
    symbols = await watchlist_repo.list_items()
    summaries: list[dict] = []
    for symbol in symbols:
        candles = await bars.get_bars(symbol, _WINDOW_INTERVAL, _WINDOW_LIMIT)
        live_price = await live.get_live_price(symbol)
        price = live_price["price"] if live_price else None
        summaries.append(metrics.summarize(symbol, candles, price))

    movers = metrics.top_movers(summaries)
    return {
        "watchlist": summaries,
        "gainers": movers["gainers"],
        "losers": movers["losers"],
        "mostVolatile": metrics.most_volatile(summaries),
        "counts": {"tracked": len(summaries)},
    }
