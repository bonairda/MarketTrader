"""Cliente mínimo de Alpaca Paper Trading.

Solo se habilita si hay credenciales configuradas. Fuerza el host de paper para
evitar operativa real por accidente. No gestiona dinero real.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("paper_trading.alpaca")


class AlpacaError(Exception):
    pass


def is_enabled() -> bool:
    return bool(
        settings.alpaca_enabled
        and settings.alpaca_api_key
        and settings.alpaca_api_secret
        and "paper" in settings.alpaca_base_url
    )


def _headers() -> dict:
    return {
        "APCA-API-KEY-ID": settings.alpaca_api_key,
        "APCA-API-SECRET-KEY": settings.alpaca_api_secret,
    }


async def _request(method: str, path: str, json: dict | None = None) -> dict:
    url = f"{settings.alpaca_base_url}{path}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.request(method, url, headers=_headers(), json=json)
            res.raise_for_status()
            return res.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300]
        raise AlpacaError(f"Alpaca {exc.response.status_code}: {detail}") from exc
    except httpx.HTTPError as exc:
        raise AlpacaError(f"Error de red con Alpaca: {exc}") from exc


async def get_account() -> dict:
    return await _request("GET", "/v2/account")


async def list_positions() -> list[dict]:
    result = await _request("GET", "/v2/positions")
    return result if isinstance(result, list) else []


async def list_orders() -> list[dict]:
    result = await _request("GET", "/v2/orders?status=all&limit=50")
    return result if isinstance(result, list) else []


async def submit_order(symbol: str, qty: str, side: str) -> dict:
    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": side.lower(),
        "type": "market",
        "time_in_force": "day",
    }
    return await _request("POST", "/v2/orders", json=payload)
