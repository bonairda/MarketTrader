"""Backfill de velas históricas.

Al añadir un activo a la watchlist se cargan sus velas recientes para que el
gráfico tenga histórico desde el primer momento, sin esperar a acumular ticks.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.modules.market_data import bars
from app.providers.base import MarketDataProvider

log = get_logger("market_data.backfill")


async def backfill_symbol(
    provider: MarketDataProvider,
    symbol: str,
    interval: str = "1m",
    limit: int = 500,
) -> int:
    """Descarga y persiste velas históricas de un símbolo. Devuelve cuántas guardó."""
    historical = await provider.fetch_historical_bars(symbol, interval=interval, limit=limit)
    count = 0
    for bar in historical:
        open_time = datetime.fromtimestamp(bar.open_time_ms / 1000, tz=UTC)
        await bars.upsert_bar(
            asset_id=bar.symbol,
            interval=interval,
            open_time=open_time,
            open_=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        count += 1
    log.info("[INGESTION] Backfill de %s: %d velas (%s)", symbol, count, interval)
    return count
