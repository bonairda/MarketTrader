"""Endpoints de eventos corporativos (dividendos y splits)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field

from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.corporate import service

router = APIRouter(prefix="/corporate-events", tags=["corporate"])


class CorporateEventIn(BaseModel):
    assetId: str = Field(min_length=1, max_length=120)
    type: str = Field(pattern="^(DIVIDEND|SPLIT)$")
    eventDate: date
    grossAmountOriginal: Decimal | None = Field(default=None, gt=0, max_digits=30, decimal_places=12)
    withholdingOriginal: Decimal | None = Field(default=None, ge=0, max_digits=30, decimal_places=12)
    currency: str | None = Field(default=None, min_length=3, max_length=12)
    fxRateToEur: Decimal | None = Field(default=None, gt=0, max_digits=24, decimal_places=12)
    ratio: Decimal | None = Field(default=None, gt=0, max_digits=24, decimal_places=12)
    externalId: str | None = Field(default=None, max_length=250)
    notes: str | None = Field(default=None, max_length=2000)

    def to_service_dict(self) -> dict:
        return {
            "asset_id": self.assetId,
            "type": self.type,
            "event_date": self.eventDate,
            "gross_amount_original": self.grossAmountOriginal,
            "withholding_original": self.withholdingOriginal,
            "currency": self.currency,
            "fx_rate_to_eur": self.fxRateToEur,
            "ratio": self.ratio,
            "external_id": self.externalId,
            "notes": self.notes,
        }


@router.get("")
async def list_events(
    year: int | None = Query(default=None, ge=1900),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await service.list_events(user.id, year=year, limit=limit, offset=offset)


@router.post("", status_code=201)
async def add_event(
    body: CorporateEventIn, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return await service.add_event(user.id, body.to_service_dict())


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: str, user: CurrentUser = Depends(get_current_user)
) -> Response:
    await service.delete_event(user.id, event_id)
    return Response(status_code=204)
