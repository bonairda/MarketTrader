"""Adaptador de cripto vía WebSocket público de Binance (gratis, tiempo real).

Se suscribe únicamente a los símbolos indicados (universo controlado) y
reconecta con backoff exponencial + jitter si la conexión se cae.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator

import httpx
import websockets

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import HistoricalBar, MarketDataProvider, Tick

log = get_logger("providers.binance")

_MAX_BACKOFF_SECONDS = 30
# Endpoint REST público de klines (velas) de Binance.
_KLINES_URL = "https://api.binance.com/api/v3/klines"


class BinanceProvider(MarketDataProvider):
    def __init__(self, ws_url: str | None = None) -> None:
        self._ws_url = ws_url or settings.crypto_ws_url

    def _build_stream_url(self, symbols: list[str]) -> str:
        # Formato de Binance: combinar streams de trades: <symbol>@trade
        streams = "/".join(f"{s.lower()}@trade" for s in symbols)
        return f"{self._ws_url}/{streams}"

    async def stream_ticks(self, symbols: list[str]) -> AsyncIterator[Tick]:
        if not symbols:
            log.warning("[INGESTION] No hay símbolos para suscribir; nada que hacer")
            return

        url = self._build_stream_url(symbols)
        attempt = 0

        while True:
            try:
                log.info("[INGESTION] Conectando a Binance WS: %s", symbols)
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    attempt = 0  # conexión ok, resetea backoff
                    async for raw in ws:
                        tick = self._parse(raw)
                        if tick is not None:
                            yield tick
            except (websockets.ConnectionClosed, OSError) as exc:
                attempt += 1
                delay = min(_MAX_BACKOFF_SECONDS, 2 ** attempt) + random.uniform(0, 1)
                log.warning(
                    "[INGESTION] Conexión perdida (%s). Reintento en %.1fs", exc, delay
                )
                await asyncio.sleep(delay)

    @staticmethod
    def _parse(raw: str | bytes) -> Tick | None:
        try:
            data = json.loads(raw)
            # Mensaje de trade de Binance: { "s": "BTCUSDT", "p": "12345.67", "T": 169... }
            return Tick(
                symbol=data["s"].lower(),
                price=float(data["p"]),
                timestamp_ms=int(data["T"]),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Mensaje de control o formato inesperado: se ignora sin romper el stream.
            return None

    async def fetch_historical_bars(
        self, symbol: str, interval: str = "1m", limit: int = 500
    ) -> list[HistoricalBar]:
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                res = await client.get(_KLINES_URL, params=params)
                res.raise_for_status()
                rows = res.json()
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("[INGESTION] Backfill fallido para %s: %s", symbol, exc)
            return []

        return [self._parse_kline(symbol, row) for row in rows if self._is_valid_kline(row)]

    @staticmethod
    def _is_valid_kline(row: object) -> bool:
        return isinstance(row, list) and len(row) >= 6

    @staticmethod
    def _parse_kline(symbol: str, row: list) -> HistoricalBar:
        # Formato Binance kline: [openTime, open, high, low, close, volume, ...]
        return HistoricalBar(
            symbol=symbol.lower(),
            open_time_ms=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )
