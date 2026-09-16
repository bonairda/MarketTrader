"""Endpoint del dashboard de inicio."""

from fastapi import APIRouter, Query

from app.modules.dashboard import service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(fresh: bool = Query(default=False)) -> dict:
    """Resumen del mercado seguido: watchlist, top movers y más volátiles.

    Con `fresh=true` se recalcula ignorando la caché.
    """
    return await service.get_dashboard(use_cache=not fresh)
