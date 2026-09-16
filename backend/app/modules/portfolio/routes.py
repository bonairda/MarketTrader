"""Endpoints de la cartera simulada."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.modules.portfolio import repository, service
from app.providers import symbols as symbol_utils

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class PositionIn(BaseModel):
    assetId: str
    quantity: float = Field(gt=0)
    averagePrice: float = Field(gt=0)


@router.get("")
async def get_portfolio() -> dict:
    return await service.get_portfolio()


@router.post("/positions", status_code=201)
async def add_position(body: PositionIn) -> dict:
    return await repository.add_position(
        asset_id=symbol_utils.normalize_asset_id(body.assetId),
        quantity=body.quantity,
        average_price=body.averagePrice,
    )


@router.delete("/positions/{position_id}", status_code=204)
async def delete_position(position_id: str) -> None:
    await repository.delete_position(position_id)
