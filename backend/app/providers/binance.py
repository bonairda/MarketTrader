"""Adaptador de cripto vía WebSocket público de Binance (gratis, tiempo real).

Se suscribe únicamente a los símbolos indicados (universo controlado) y
reconecta con backoff exponencial + jitter si la conexión se cae.
"""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import AsyncIterator

import websockets

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import MarketDataProvider, Tick

log = get_logger("providers.binance")

_MAX_BACKOFF_SECONDS = 30


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
