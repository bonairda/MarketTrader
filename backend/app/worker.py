"""Worker de ingestión.

Se suscribe a los activos de la watchlist (o a los símbolos por defecto si
está vacía), actualiza el precio en vivo en Redis y agrega velas de 1m que se
persisten al cerrarse. Los ticks NO se guardan en base de datos.

Arquitectura de tareas:
  - `_ingest`: consume el stream de ticks (reactivo).
  - `_maintenance`: tarea periódica que cierra velas vencidas (flush_stale) y
    recarga las reglas de alerta, aunque no lleguen ticks.
Al apagar, persiste las velas en construcción (flush_all).
"""

from __future__ import annotations

import asyncio
import time

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.redis_client import close_redis
from app.modules.alerts.engine import AlertEngine
from app.modules.market_data import live
from app.modules.market_data.aggregator import BarAggregator
from app.modules.notifications import telegram
from app.modules.watchlists import repository as watchlist_repo
from app.providers.binance import BinanceProvider

# Cada cuántos segundos el worker recarga las reglas de alerta desde la BD.
_RULES_REFRESH_SECONDS = 30
# Cada cuántos segundos se comprueban velas vencidas y el estado de ingestión.
_MAINTENANCE_INTERVAL_SECONDS = 5


class IngestionMonitor:
    """Registra la última vez que se recibió un tick, para el watchdog."""

    def __init__(self) -> None:
        self.last_tick_at: float = time.time()
        self._alerted = False

    def mark_tick(self) -> None:
        self.last_tick_at = time.time()
        if self._alerted:
            self._alerted = False
            log.info("[WATCHDOG] Ingestión recuperada")

    async def check(self) -> None:
        stale_for = time.time() - self.last_tick_at
        if stale_for >= settings.ingestion_stale_seconds and not self._alerted:
            self._alerted = True
            msg = (
                f"[MarketTracker] Sin datos de mercado desde hace "
                f"{int(stale_for)}s. La ingestión puede estar caída."
            )
            log.warning("[WATCHDOG] %s", msg)
            await telegram.send_message(msg)

setup_logging()
log = get_logger("worker")


async def _resolve_symbols() -> list[str]:
    """Universo controlado: watchlist si tiene elementos, si no los de por defecto."""
    symbols = await watchlist_repo.list_items()
    if not symbols:
        symbols = settings.crypto_symbols
        log.info("[INGESTION] Watchlist vacía; usando símbolos por defecto: %s", symbols)
    return symbols


async def _ingest(
    provider: BinanceProvider,
    symbols: list[str],
    aggregator: BarAggregator,
    alert_engine: AlertEngine,
    monitor: IngestionMonitor,
) -> None:
    log.info("[INGESTION] Iniciando ingestión para: %s", symbols)
    async for tick in provider.stream_ticks(symbols):
        monitor.mark_tick()
        await live.set_live_price(tick.symbol, tick.price, tick.timestamp_ms)
        await aggregator.on_tick(tick.symbol, tick.price, tick.timestamp_ms)
        await alert_engine.on_tick(tick.symbol, tick.price)


async def _maintenance(
    aggregator: BarAggregator, alert_engine: AlertEngine, monitor: IngestionMonitor
) -> None:
    """Cierra velas vencidas, recarga reglas y vigila la ingestión (watchdog)."""
    seconds_since_rules = 0
    while True:
        await asyncio.sleep(_MAINTENANCE_INTERVAL_SECONDS)
        await aggregator.flush_stale()
        await monitor.check()
        seconds_since_rules += _MAINTENANCE_INTERVAL_SECONDS
        if seconds_since_rules >= _RULES_REFRESH_SECONDS:
            await alert_engine.refresh_rules()
            seconds_since_rules = 0


async def run() -> None:
    aggregator = BarAggregator()
    alert_engine = AlertEngine()
    provider = BinanceProvider()
    monitor = IngestionMonitor()

    await alert_engine.refresh_rules()
    symbols = await _resolve_symbols()

    ingest_task = asyncio.create_task(
        _ingest(provider, symbols, aggregator, alert_engine, monitor)
    )
    maintenance_task = asyncio.create_task(
        _maintenance(aggregator, alert_engine, monitor)
    )

    try:
        await asyncio.gather(ingest_task, maintenance_task)
    finally:
        maintenance_task.cancel()
        ingest_task.cancel()
        # Persistir las velas en construcción antes de salir.
        await aggregator.flush_all()


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
