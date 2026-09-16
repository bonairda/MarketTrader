"""Evaluación periódica de mercados llamativos sobre la watchlist.

Recorre los activos seguidos, detecta anomalías y notifica (con cooldown por
símbolo+motivo para no repetir el mismo aviso). Se llama desde el worker.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.modules.market_data import bars
from app.modules.notifications import dispatcher
from app.modules.signals import hotmarkets
from app.modules.watchlists import repository as watchlist_repo

log = get_logger("signals.hotmarkets")

_COOLDOWN_KEY = "hotmarket:cooldown:"  # + symbol:reason
_COOLDOWN_SECONDS = 900  # 15 min entre avisos del mismo tipo para un símbolo
_INTERVAL = "1m"
_LIMIT = 60


async def evaluate_watchlist() -> None:
    # Unión de todas las watchlists: los mercados llamativos son condiciones de
    # mercado (globales), no dependen de un usuario concreto.
    symbols = await watchlist_repo.list_all_symbols()
    for symbol in symbols:
        candles = await bars.get_bars(symbol, _INTERVAL, _LIMIT)
        hit = hotmarkets.detect(symbol, candles)
        if hit is not None and await _acquire_cooldown(symbol, hit.reason):
            message = f"Mercado llamativo · {symbol.upper()}: {hit.detail}"
            log.info("[HOTMARKET] %s", message)
            await dispatcher.notify(message)


async def _acquire_cooldown(symbol: str, reason: str) -> bool:
    """Evita repetir el mismo aviso (símbolo+motivo) en la ventana de cooldown."""
    redis = get_redis()
    key = f"{_COOLDOWN_KEY}{symbol}:{reason}"
    acquired = await redis.set(key, "1", nx=True, ex=_COOLDOWN_SECONDS)
    return bool(acquired)
