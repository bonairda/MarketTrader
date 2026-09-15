"""Agregador de velas de 1 minuto en memoria.

Mantiene la vela en construcción por símbolo. Cierra y persiste una vela cuando:
  - llega un tick de un minuto posterior (rollover normal), o
  - `flush_stale()` detecta que el minuto de la vela ya terminó aunque no lleguen
    más ticks de ese símbolo (evita perder velas de activos poco líquidos), o
  - `flush_all()` en el apagado del worker (no perder la vela en curso).

La persistencia es idempotente (upsert por asset+interval+open_time), así que
volver a cerrar una vela ya guardada no causa problemas.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.modules.market_data import bars

log = get_logger("market_data.aggregator")

_INTERVAL = "1m"
_SECONDS_PER_MINUTE = 60


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
        minute = timestamp_ms // 1000 // _SECONDS_PER_MINUTE
        current = self._building.get(symbol)

        if current is None:
            self._building[symbol] = _Building(minute, price, price, price, price)
            return

        if minute == current.minute:
            current.high = max(current.high, price)
            current.low = min(current.low, price)
            current.close = price
            return

        if minute < current.minute:
            # Tick fuera de orden (más antiguo que la vela en curso): se ignora.
            log.debug("[AGG] Tick fuera de orden en %s, ignorado", symbol)
            return

        # Minuto nuevo: cierra y persiste la vela anterior, y abre una nueva.
        await self._flush(symbol, current)
        self._building[symbol] = _Building(minute, price, price, price, price)

    async def flush_stale(self, now_ms: int | None = None) -> None:
        """Cierra las velas cuyo minuto ya terminó, aunque no lleguen más ticks.

        Debe llamarse periódicamente (p. ej. cada pocos segundos) para no dejar
        colgada la vela de un símbolo que dejó de operar.
        """
        now = now_ms if now_ms is not None else int(time.time() * 1000)
        current_minute = now // 1000 // _SECONDS_PER_MINUTE
        stale_symbols = [
            s for s, b in self._building.items() if b.minute < current_minute
        ]
        for symbol in stale_symbols:
            await self._flush(symbol, self._building.pop(symbol))

    async def flush_all(self) -> None:
        """Persiste todas las velas en construcción (usar en el apagado)."""
        for symbol, bar in list(self._building.items()):
            await self._flush(symbol, bar)
        self._building.clear()

    async def _flush(self, symbol: str, bar: _Building) -> None:
        open_time = datetime.fromtimestamp(
            bar.minute * _SECONDS_PER_MINUTE, tz=timezone.utc
        )
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
