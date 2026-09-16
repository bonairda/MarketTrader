"""Endpoints de reglas de alerta."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.errors import NotFoundError
from app.modules.alerts import repository
from app.modules.auth.deps import CurrentUser, get_current_user
from app.providers import symbols as symbol_utils

router = APIRouter(prefix="/alerts", tags=["alerts"])

_VALID_TYPES = {"PRICE_CROSS", "PERCENT_CHANGE", "INDICATOR_CROSS"}
_VALID_INDICATORS = {"rsi14", "sma20", "ema20"}


class AlertRuleIn(BaseModel):
    assetId: str
    type: str = Field(default="PRICE_CROSS")
    direction: str = Field(pattern="^(ABOVE|BELOW)$")
    threshold: float
    indicator: str | None = None
    timeframe: str = "1m"
    channels: str = "TELEGRAM"
    cooldownSeconds: int = Field(default=300, ge=0)

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in _VALID_TYPES:
            raise ValueError(f"type debe ser uno de {sorted(_VALID_TYPES)}")
        return v


class EnabledIn(BaseModel):
    enabled: bool


def _validate_rule(rule: AlertRuleIn) -> None:
    """Validaciones cruzadas por tipo (más allá de las de campo)."""
    if rule.type in ("PRICE_CROSS", "INDICATOR_CROSS") and rule.threshold <= 0:
        raise HTTPException(422, "threshold debe ser > 0 para este tipo de alerta")
    if rule.type == "INDICATOR_CROSS":
        indicator = rule.indicator or "rsi14"
        if indicator not in _VALID_INDICATORS:
            raise HTTPException(422, f"indicator debe ser uno de {sorted(_VALID_INDICATORS)}")


@router.get("")
async def list_alerts(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return await repository.list_rules(user.id)


@router.post("", status_code=201)
async def create_alert(
    rule: AlertRuleIn, user: CurrentUser = Depends(get_current_user)
) -> dict:
    _validate_rule(rule)
    indicator = rule.indicator or ("rsi14" if rule.type == "INDICATOR_CROSS" else None)
    return await repository.create_rule(
        user_id=user.id,
        asset_id=symbol_utils.normalize_asset_id(rule.assetId),
        rule_type=rule.type,
        direction=rule.direction,
        threshold=rule.threshold,
        indicator=indicator,
        timeframe=rule.timeframe,
        channels=rule.channels,
        cooldown_seconds=rule.cooldownSeconds,
    )


@router.put("/{rule_id}/enabled")
async def set_enabled(
    rule_id: str, body: EnabledIn, user: CurrentUser = Depends(get_current_user)
) -> dict:
    affected = await repository.set_enabled(user.id, rule_id, body.enabled)
    if affected == 0:
        raise NotFoundError("Alerta no encontrada")
    return {"id": rule_id, "enabled": body.enabled}


@router.delete("/{rule_id}", status_code=204)
async def delete_alert(
    rule_id: str, user: CurrentUser = Depends(get_current_user)
) -> None:
    affected = await repository.delete_rule(user.id, rule_id)
    if affected == 0:
        raise NotFoundError("Alerta no encontrada")
