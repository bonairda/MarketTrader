"""Contrato común de proveedores de datos de mercado.

Todo proveedor (cripto, forex, acciones) implementa esta interfaz para que el
resto de la aplicación no dependa de ningún proveedor concreto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class Tick:
    """Un cambio de precio normalizado. NO se persiste; solo se usa en memoria/Redis."""

    symbol: str
    price: float
    timestamp_ms: int


@dataclass
class HistoricalBar:
    """Una vela histórica normalizada (para backfill)."""

    symbol: str
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class MarketDataProvider(ABC):
    """Interfaz que todos los adaptadores de proveedores deben implementar."""

    @abstractmethod
    def stream_ticks(self, symbols: list[str]) -> AsyncIterator[Tick]:
        """Emite ticks normalizados para los símbolos suscritos.

        Las implementaciones son generadores asíncronos (`async def ... yield`)
        y deben gestionar la reconexión internamente, sin romper el bucle
        consumidor ante caídas puntuales de red.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_historical_bars(
        self, symbol: str, interval: str = "1m", limit: int = 500
    ) -> list[HistoricalBar]:
        """Devuelve velas históricas recientes para el backfill de un activo."""
        raise NotImplementedError
