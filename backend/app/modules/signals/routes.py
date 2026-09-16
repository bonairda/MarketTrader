"""Endpoints de señales."""

from fastapi import APIRouter, Depends, Query

from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.signals import service

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/{symbol}")
async def get_signal(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=500, le=1000),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Señal (BUY/SELL/HOLD/WATCH) con rationale y riesgo para un activo."""
    return await service.get_signal(symbol.lower(), interval, limit)
