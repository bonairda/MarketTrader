"""Endpoints de la watchlist."""

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.modules.market_data.backfill import backfill_symbol
from app.modules.watchlists import repository
from app.providers.binance import BinanceProvider

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistItemIn(BaseModel):
    assetId: str
    notes: str | None = None


@router.get("")
async def get_watchlist() -> list[str]:
    return await repository.list_items()


@router.post("", status_code=201)
async def add_to_watchlist(item: WatchlistItemIn, background: BackgroundTasks) -> dict:
    asset_id = item.assetId.lower()
    await repository.add_item(asset_id, item.notes)
    # Backfill del histórico en segundo plano para no bloquear la respuesta.
    background.add_task(backfill_symbol, BinanceProvider(), asset_id)
    return {"assetId": asset_id}


@router.delete("/{asset_id}", status_code=204)
async def remove_from_watchlist(asset_id: str) -> None:
    await repository.remove_item(asset_id.lower())
