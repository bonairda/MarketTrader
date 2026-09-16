"""Endpoint de consulta de tipos de cambio a EUR."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.errors import NotFoundError
from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.fx import service

router = APIRouter(prefix="/fx", tags=["fx"])


@router.get("/rate")
async def fx_rate(
    currency: str = Query(min_length=3, max_length=12),
    on: date | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Cambio divisa->EUR (1 divisa = N EUR) para la fecha indicada (hoy si falta)."""
    result = await service.get_rate_to_eur(currency, on or date.today())
    if result is None:
        raise NotFoundError("No hay tipo de cambio disponible para esa divisa/fecha")
    return result
