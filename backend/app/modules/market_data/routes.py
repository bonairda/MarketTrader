"""Endpoints de datos de mercado: precio en vivo (Redis) y velas (BD)."""

from fastapi import APIRouter, Query

from app.modules.market_data import bars, live
from app.modules.watchlists import repository as watchlist_repo

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices")
async def live_prices() -> list[dict]:
    """Precio en vivo de todos los activos de la watchlist."""
    symbols = await watchlist_repo.list_items()
    return await live.get_live_prices(symbols)


@router.get("/prices/{symbol}")
async def live_price(symbol: str) -> dict | None:
    return await live.get_live_price(symbol.lower())


@router.get("/bars/{symbol}")
async def get_bars(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=200, le=1000),
) -> list[dict]:
    return await bars.get_bars(symbol.lower(), interval, limit)
