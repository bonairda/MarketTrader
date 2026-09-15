"""Endpoints de la watchlist."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.watchlists import repository

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistItemIn(BaseModel):
    assetId: str
    notes: str | None = None


@router.get("")
async def get_watchlist() -> list[str]:
    return await repository.list_items()


@router.post("", status_code=201)
async def add_to_watchlist(item: WatchlistItemIn) -> dict:
    await repository.add_item(item.assetId, item.notes)
    return {"assetId": item.assetId}


@router.delete("/{asset_id}", status_code=204)
async def remove_from_watchlist(asset_id: str) -> None:
    await repository.remove_item(asset_id)
