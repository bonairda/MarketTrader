"""Endpoint de backtesting."""

from fastapi import APIRouter, Query

from app.modules.backtest import service

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/{symbol}")
async def run_backtest(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=1000, le=5000),
) -> dict:
    """Ejecuta la estrategia de señales sobre las velas históricas y devuelve métricas."""
    return await service.run_backtest(symbol.lower(), interval, limit)
