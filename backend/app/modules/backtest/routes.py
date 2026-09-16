"""Endpoint de backtesting."""

from fastapi import APIRouter, Depends, Query

from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.backtest import service
from app.providers.symbols import normalize_asset_id

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/{symbol:path}")
async def run_backtest(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=1000, le=5000),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Ejecuta la estrategia de señales sobre las velas históricas y devuelve métricas."""
    return await service.run_backtest(normalize_asset_id(symbol), interval, limit)
