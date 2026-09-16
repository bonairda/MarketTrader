"""Worker de ingestión.

Se suscribe a los activos de la watchlist (o a los símbolos por defecto si
está vacía), actualiza el precio en vivo en Redis y agrega velas de 1m que se
persisten al cerrarse. Los ticks NO se guardan en base de datos.

Arquitectura de tareas:
  - `_ingest`: consume el stream de ticks (reactivo). Se reinicia cuando cambia
    la watchlist (resuscripción en caliente, sin reiniciar el proceso).
  - `_maintenance`: tarea periódica que cierra velas vencidas (flush_stale),
    recarga las reglas de alerta y vigila la ingestión (watchdog).
  - `_watch_watchlist`: escucha el canal Redis de cambios de watchlist.
Al apagar, persiste las velas en construcción (flush_all).
"""

from __future__ import annotations

import asyncio
import time

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.redis_client import close_redis, get_redis
from app.modules.alerts.engine import AlertEngine
from app.modules.market_data import live
from app.modules.market_data.aggregator import BarAggregator
from app.modules.notifications import dispatcher
from app.modules.watchlists import repository as watchlist_repo
from app.modules.watchlists.events import WATCHLIST_CHANGED_CHANNEL
from app.providers import symbols as symbol_utils
from app.providers.base import MarketDataProvider
from app.providers.binance import BinanceProvider
from app.providers.symbols import ProviderKind
from app.providers.twelve_data import TwelveDataProvider

setup_logging()
log = get_logger("worker")

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
            await dispatcher.notify(msg)


async def _resolve_symbols() -> list[str]:
    """Universo controlado: watchlist si tiene elementos, si no los de por defecto."""
    symbols = await watchlist_repo.list_items()
    if not symbols:
        symbols = settings.crypto_symbols
        log.info("[INGESTION] Watchlist vacía; usando símbolos por defecto: %s", symbols)
    return symbols


async def _ingest(
    provider: MarketDataProvider,
    symbols: list[str],
    aggregator: BarAggregator,
    alert_engine: AlertEngine,
    monitor: IngestionMonitor,
) -> None:
    log.info("[INGESTION] Iniciando ingestión (%s) para: %s", type(provider).__name__, symbols)
    async for tick in provider.stream_ticks(symbols):
        monitor.mark_tick()
        await live.set_live_price(tick.symbol, tick.price, tick.timestamp_ms)
        await aggregator.on_tick(tick.symbol, tick.price, tick.timestamp_ms)
        await alert_engine.on_tick(tick.symbol, tick.price)


def _providers_for(grouped: dict[ProviderKind, list[str]]) -> list[tuple[MarketDataProvider, list[str]]]:
    """Empareja cada proveedor con sus símbolos, según el enrutado por prefijo."""
    pairs: list[tuple[MarketDataProvider, list[str]]] = []
    if ProviderKind.CRYPTO in grouped:
        pairs.append((BinanceProvider(), grouped[ProviderKind.CRYPTO]))
    if ProviderKind.TWELVE_DATA in grouped:
        pairs.append((TwelveDataProvider(), grouped[ProviderKind.TWELVE_DATA]))
    return pairs


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


async def _watch_watchlist(changed: asyncio.Event) -> None:
    """Activa el evento `changed` cuando la watchlist cambia (canal Redis)."""
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(WATCHLIST_CHANGED_CHANNEL)
    try:
        async for message in pubsub.listen():
            if message.get("type") == "message":
                log.info("[INGESTION] Watchlist cambiada; se resuscribirá")
                changed.set()
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe(WATCHLIST_CHANGED_CHANNEL)
        await pubsub.aclose()


async def run() -> None:
    aggregator = BarAggregator()
    alert_engine = AlertEngine()
    monitor = IngestionMonitor()

    await alert_engine.refresh_rules()

    changed = asyncio.Event()
    maintenance_task = asyncio.create_task(_maintenance(aggregator, alert_engine, monitor))
    watchlist_task = asyncio.create_task(_watch_watchlist(changed))

    try:
        # Bucle supervisor: agrupa los símbolos por proveedor (cripto vía Binance,
        # acciones/forex vía Twelve Data), lanza un stream por proveedor y los
        # reinicia todos cuando la watchlist cambia.
        while True:
            symbols = await _resolve_symbols()
            grouped = symbol_utils.group_by_provider(symbols)

            ingest_tasks = [
                asyncio.create_task(
                    _ingest(provider, provider_symbols, aggregator, alert_engine, monitor)
                )
                for provider, provider_symbols in _providers_for(grouped)
            ]
            changed_wait = asyncio.create_task(changed.wait())

            await asyncio.wait(
                {*ingest_tasks, changed_wait},
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancela todos los streams antes de resuscribir (o al salir).
            for task in ingest_tasks:
                task.cancel()
            changed_wait.cancel()

            if changed.is_set():
                changed.clear()
                log.info("[INGESTION] Resuscribiendo a la nueva watchlist")
                continue
            # Si un stream terminó por sí solo (caso raro), reintenta.
            await asyncio.sleep(1)
    finally:
        maintenance_task.cancel()
        watchlist_task.cancel()
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
