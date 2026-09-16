"""Endpoint del dashboard de inicio."""

from fastapi import APIRouter, Depends, Query

from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.dashboard import service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    fresh: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Resumen del mercado seguido: watchlist, top movers y más volátiles.

    Con `fresh=true` se recalcula ignorando la caché.
    """
    return await service.get_dashboard(user.id, use_cache=not fresh)
