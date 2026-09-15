"""Agregador de velas de 1 minuto en memoria.

Mantiene la vela en construcción por símbolo. Cuando llega un tick de un minuto
nuevo, cierra la vela anterior y la persiste (única escritura a la BD).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.modules.market_data import bars

log = get_logger("market_data.aggregator")

_INTERVAL = "1m"


@dataclass
class _Building:
    minute: int  # epoch en minutos
    open: float
    high: float
    low: float
    close: float


class BarAggregator:
    """Agrega ticks en velas de 1m. Una instancia por proceso worker."""

    def __init__(self) -> None:
        self._building: dict[str, _Building] = {}

    async def on_tick(self, symbol: str, price: float, timestamp_ms: int) -> None:
        minute = timestamp_ms // 1000 // 60
        current = self._building.get(symbol)

        if current is None:
            self._building[symbol] = _Building(minute, price, price, price, price)
            return

        if minute == current.minute:
            # Mismo minuto: actualiza la vela en curso.
            current.high = max(current.high, price)
            current.low = min(current.low, price)
            current.close = price
            return

        # Minuto nuevo: cierra y persiste la vela anterior, y abre una nueva.
        await self._flush(symbol, current)
        self._building[symbol] = _Building(minute, price, price, price, price)

    async def _flush(self, symbol: str, bar: _Building) -> None:
        open_time = datetime.fromtimestamp(bar.minute * 60, tz=timezone.utc)
        try:
            await bars.upsert_bar(
                asset_id=symbol,
                interval=_INTERVAL,
                open_time=open_time,
                o=bar.open,
                h=bar.high,
                l=bar.low,
                c=bar.close,
            )
        except Exception as exc:  # no romper la ingestión por un fallo de BD
            log.error("[DB] Error guardando vela de %s: %s", symbol, exc)
