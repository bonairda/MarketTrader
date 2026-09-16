"""Endpoints de paper trading (Alpaca, sin dinero real)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.modules.auth.deps import CurrentUser, get_current_user, require_role
from app.modules.paper_trading import service

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])


class PaperOrderIn(BaseModel):
    assetId: str = Field(min_length=1, max_length=120)
    side: str = Field(pattern="^(BUY|SELL)$")
    quantity: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    confirm: bool = False


@router.get("/status")
async def paper_status(user: CurrentUser = Depends(get_current_user)) -> dict:
    return service.status()


@router.get("/account")
async def paper_account(user: CurrentUser = Depends(get_current_user)) -> dict:
    return await service.get_account()


@router.get("/positions")
async def paper_positions(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return await service.get_positions()


@router.get("/orders")
async def paper_orders(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return await service.get_orders()


@router.post("/orders")
async def submit_paper_order(
    body: PaperOrderIn,
    user: CurrentUser = Depends(require_role("OWNER")),
) -> dict:
    return await service.submit_order(
        body.assetId, format(body.quantity, "f"), body.side, confirm=body.confirm
    )
