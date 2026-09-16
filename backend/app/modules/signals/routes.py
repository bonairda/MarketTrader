"""Endpoints de señales."""

from fastapi import APIRouter, Query

from app.modules.signals import service

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/{symbol}")
async def get_signal(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=500, le=1000),
) -> dict:
    """Señal (BUY/SELL/HOLD/WATCH) con rationale y riesgo para un activo."""
    return await service.get_signal(symbol.lower(), interval, limit)
