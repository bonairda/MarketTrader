"""Endpoints de la cartera simulada."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.errors import NotFoundError
from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.portfolio import repository, service
from app.providers import symbols as symbol_utils

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PositionIn(BaseModel):
    assetId: str
    quantity: float = Field(gt=0)
    averagePrice: float = Field(gt=0)


@router.get("")
async def get_portfolio(user: CurrentUser = Depends(get_current_user)) -> dict:
    return await service.get_portfolio(user.id)


@router.post("/positions", status_code=201)
async def add_position(
    body: PositionIn, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return await repository.add_position(
        user_id=user.id,
        asset_id=symbol_utils.normalize_asset_id(body.assetId),
        quantity=body.quantity,
        average_price=body.averagePrice,
    )


@router.delete("/positions/{position_id}", status_code=204)
async def delete_position(
    position_id: str, user: CurrentUser = Depends(get_current_user)
) -> None:
    affected = await repository.delete_position(user.id, position_id)
    if affected == 0:
        raise NotFoundError("Posición no encontrada")
