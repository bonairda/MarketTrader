"""Endpoints de la watchlist."""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.market_data.backfill import backfill_symbol
from app.modules.watchlists import repository
from app.providers import symbols as symbol_utils
from app.providers.base import MarketDataProvider
from app.providers.binance import BinanceProvider
from app.providers.symbols import ProviderKind
from app.providers.twelve_data import TwelveDataProvider


def _provider_for(asset_id: str) -> MarketDataProvider:
    if symbol_utils.provider_for(asset_id) == ProviderKind.TWELVE_DATA:
        return TwelveDataProvider()
    return BinanceProvider()

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistItemIn(BaseModel):
    assetId: str
    notes: str | None = None


@router.get("")
async def get_watchlist(user: CurrentUser = Depends(get_current_user)) -> list[str]:
    return await repository.list_items(user.id)


@router.post("", status_code=201)
async def add_to_watchlist(
    item: WatchlistItemIn,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    asset_id = symbol_utils.normalize_asset_id(item.assetId)
    await repository.add_item(user.id, asset_id, item.notes)
    # Backfill del histórico en segundo plano para no bloquear la respuesta,
    # usando el proveedor que corresponde al tipo de símbolo. El histórico de
    # velas es compartido, así que basta con hacerlo una vez por símbolo.
    background.add_task(backfill_symbol, _provider_for(asset_id), asset_id)
    return {"assetId": asset_id}


@router.delete("/{asset_id}", status_code=204)
async def remove_from_watchlist(
    asset_id: str, user: CurrentUser = Depends(get_current_user)
) -> None:
    await repository.remove_item(user.id, symbol_utils.normalize_asset_id(asset_id))
