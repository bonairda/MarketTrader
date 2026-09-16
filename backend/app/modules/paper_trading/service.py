"""Servicio de paper trading. Requiere confirmación explícita para operar."""

from __future__ import annotations

from app.core.errors import AppError
from app.modules.paper_trading import alpaca
from app.providers.symbols import STOCK_PREFIX


def _ensure_enabled() -> None:
    if not alpaca.is_enabled():
        raise AppError(
            "Paper trading no está habilitado (configura ALPACA_* con host paper)",
            code="PAPER_TRADING_DISABLED",
            status_code=409,
        )


def _to_alpaca_symbol(asset_id: str) -> str:
    """Alpaca opera acciones US por ticker; solo se permiten activos stock:."""
    if not asset_id.startswith(STOCK_PREFIX):
        raise AppError(
            "El paper trading solo admite acciones (stock:TICKER)",
            code="UNSUPPORTED_PAPER_ASSET",
            status_code=422,
        )
    return asset_id[len(STOCK_PREFIX):]


def status() -> dict:
    return {"enabled": alpaca.is_enabled(), "mode": "paper"}


async def get_account() -> dict:
    _ensure_enabled()
    try:
        return await alpaca.get_account()
    except alpaca.AlpacaError as exc:
        raise AppError(str(exc), code="PAPER_TRADING_ERROR", status_code=502) from exc


async def get_positions() -> list[dict]:
    _ensure_enabled()
    try:
        return await alpaca.list_positions()
    except alpaca.AlpacaError as exc:
        raise AppError(str(exc), code="PAPER_TRADING_ERROR", status_code=502) from exc


async def get_orders() -> list[dict]:
    _ensure_enabled()
    try:
        return await alpaca.list_orders()
    except alpaca.AlpacaError as exc:
        raise AppError(str(exc), code="PAPER_TRADING_ERROR", status_code=502) from exc


async def submit_order(asset_id: str, quantity: str, side: str, *, confirm: bool) -> dict:
    _ensure_enabled()
    if not confirm:
        raise AppError(
            "Debes confirmar explícitamente la orden simulada",
            code="CONFIRMATION_REQUIRED",
            status_code=422,
        )
    if side.upper() not in {"BUY", "SELL"}:
        raise AppError("Lado no válido", code="INVALID_SIDE", status_code=422)
    symbol = _to_alpaca_symbol(asset_id)
    try:
        order = await alpaca.submit_order(symbol, quantity, side)
    except alpaca.AlpacaError as exc:
        raise AppError(str(exc), code="PAPER_TRADING_ERROR", status_code=502) from exc
    return {
        "id": order.get("id"),
        "symbol": symbol,
        "side": side.upper(),
        "quantity": quantity,
        "status": order.get("status"),
        "submittedAt": order.get("submitted_at"),
    }
