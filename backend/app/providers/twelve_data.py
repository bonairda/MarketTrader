"""Adaptador de acciones y forex vía Twelve Data (plan gratuito: polling REST).

El plan gratuito no ofrece WebSocket, así que `stream_ticks` hace polling del
endpoint /price cada `twelve_data_poll_seconds` y emite un tick por símbolo con
el último precio (con retraso ~15 min en acciones, asumido en el diseño).

Los `asset_id` llegan con prefijo (stock:/fx:); se traducen al símbolo del
proveedor con `symbols.to_provider_symbol`.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.providers import symbols as symbol_utils
from app.providers.base import HistoricalBar, MarketDataProvider, Tick

log = get_logger("providers.twelve_data")

_BASE_URL = "https://api.twelvedata.com"


class TwelveDataProvider(MarketDataProvider):
    def __init__(self, api_key: str | None = None, poll_seconds: int | None = None) -> None:
        self._api_key = api_key or settings.twelve_data_api_key
        self._poll_seconds = poll_seconds or settings.twelve_data_poll_seconds

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def stream_ticks(self, symbols: list[str]) -> AsyncIterator[Tick]:
        if not symbols:
            return
        if not self.is_available():
            log.warning("[INGESTION] Twelve Data sin API key; no se ingieren acciones/forex")
            return

        # Mapa símbolo-proveedor -> asset_id interno, para devolver el tick con
        # el asset_id original (con prefijo).
        provider_to_asset = {symbol_utils.to_provider_symbol(a): a for a in symbols}
        provider_symbols = list(provider_to_asset.keys())

        while True:
            prices = await self._fetch_prices(provider_symbols)
            now_ms = int(time.time() * 1000)
            for provider_symbol, price in prices.items():
                asset_id = provider_to_asset.get(provider_symbol)
                if asset_id is not None:
                    yield Tick(symbol=asset_id, price=price, timestamp_ms=now_ms)
            await asyncio.sleep(self._poll_seconds)

    async def _fetch_prices(self, provider_symbols: list[str]) -> dict[str, float]:
        """Consulta /price para uno o varios símbolos. Devuelve {símbolo: precio}."""
        params = {"symbol": ",".join(provider_symbols), "apikey": self._api_key}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.get(f"{_BASE_URL}/price", params=params)
                res.raise_for_status()
                data = res.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("[INGESTION] Twelve Data /price falló: %s", exc)
            return {}
        return self._parse_prices(provider_symbols, data)

    @staticmethod
    def _parse_prices(provider_symbols: list[str], data: dict) -> dict[str, float]:
        """Normaliza la respuesta de /price.

        Con un símbolo, Twelve Data devuelve {"price": "1.23"}.
        Con varios, devuelve {"AAPL": {"price": "1.23"}, ...}.
        """
        result: dict[str, float] = {}
        if len(provider_symbols) == 1:
            price = data.get("price")
            if price is not None:
                try:
                    result[provider_symbols[0]] = float(price)
                except (TypeError, ValueError):
                    pass
            return result

        for symbol in provider_symbols:
            entry = data.get(symbol)
            if isinstance(entry, dict) and entry.get("price") is not None:
                try:
                    result[symbol] = float(entry["price"])
                except (TypeError, ValueError):
                    pass
        return result

    async def fetch_historical_bars(
        self, symbol: str, interval: str = "1m", limit: int = 500
    ) -> list[HistoricalBar]:
        if not self.is_available():
            return []
        provider_symbol = symbol_utils.to_provider_symbol(symbol)
        params = {
            "symbol": provider_symbol,
            "interval": _to_td_interval(interval),
            "outputsize": min(limit, 5000),
            "apikey": self._api_key,
            "order": "ASC",
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                res = await client.get(f"{_BASE_URL}/time_series", params=params)
                res.raise_for_status()
                data = res.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("[INGESTION] Backfill Twelve Data falló para %s: %s", symbol, exc)
            return []

        values = data.get("values")
        if not isinstance(values, list):
            log.warning("[INGESTION] Twelve Data sin datos para %s: %s", symbol, data.get("message"))
            return []
        return [bar for row in values if (bar := self._parse_bar(symbol, row)) is not None]

    @staticmethod
    def _parse_bar(asset_id: str, row: dict) -> HistoricalBar | None:
        try:
            # datetime viene como "2024-01-01 12:34:00" (UTC en el plan estándar).
            dt = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S")
            open_time_ms = int(dt.replace(tzinfo=UTC).timestamp() * 1000)
            return HistoricalBar(
                symbol=asset_id,
                open_time_ms=open_time_ms,
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]) if row.get("volume") not in (None, "") else None,
            )
        except (KeyError, ValueError, TypeError):
            return None


def _to_td_interval(interval: str) -> str:
    """Traduce nuestros intervalos al formato de Twelve Data."""
    mapping = {"1m": "1min", "5m": "5min", "1h": "1h", "1d": "1day"}
    return mapping.get(interval, "1min")
