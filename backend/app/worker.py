"""Worker de ingestión.

Se suscribe a los activos de la watchlist (o a los símbolos por defecto si
está vacía), actualiza el precio en vivo en Redis y agrega velas de 1m que se
persisten al cerrarse. Los ticks NO se guardan en base de datos.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.db import init_db
from app.core.logging import get_logger, setup_logging
from app.core.redis_client import close_redis
from app.modules.market_data import live
from app.modules.market_data.aggregator import BarAggregator
from app.modules.watchlists import repository as watchlist_repo
from app.providers.binance import BinanceProvider

setup_logging()
log = get_logger("worker")


async def _resolve_symbols() -> list[str]:
    """Universo controlado: watchlist si tiene elementos, si no los de por defecto."""
    symbols = await watchlist_repo.list_items()
    if not symbols:
        symbols = settings.crypto_symbols
        log.info("[INGESTION] Watchlist vacía; usando símbolos por defecto: %s", symbols)
    return symbols


async def run() -> None:
    await init_db()
    aggregator = BarAggregator()
    provider = BinanceProvider()

    symbols = await _resolve_symbols()
    log.info("[INGESTION] Iniciando ingestión para: %s", symbols)

    async for tick in provider.stream_ticks(symbols):
        await live.set_live_price(tick.symbol, tick.price, tick.timestamp_ms)
        await aggregator.on_tick(tick.symbol, tick.price, tick.timestamp_ms)


async def main() -> None:
    try:
        await run()
    finally:
        await close_redis()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("[INFO] Worker detenido")
