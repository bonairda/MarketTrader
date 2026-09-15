"""Endpoints de reglas de alerta."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.modules.alerts import repository

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRuleIn(BaseModel):
    assetId: str
    direction: str = Field(pattern="^(ABOVE|BELOW)$")
    threshold: float = Field(gt=0)
    channels: str = "TELEGRAM"
    cooldownSeconds: int = Field(default=300, ge=0)


class EnabledIn(BaseModel):
    enabled: bool


@router.get("")
async def list_alerts() -> list[dict]:
    return await repository.list_rules()


@router.post("", status_code=201)
async def create_alert(rule: AlertRuleIn) -> dict:
    return await repository.create_rule(
        asset_id=rule.assetId.lower(),
        direction=rule.direction,
        threshold=rule.threshold,
        channels=rule.channels,
        cooldown_seconds=rule.cooldownSeconds,
    )


@router.put("/{rule_id}/enabled")
async def set_enabled(rule_id: str, body: EnabledIn) -> dict:
    await repository.set_enabled(rule_id, body.enabled)
    return {"id": rule_id, "enabled": body.enabled}


@router.delete("/{rule_id}", status_code=204)
async def delete_alert(rule_id: str) -> None:
    await repository.delete_rule(rule_id)
