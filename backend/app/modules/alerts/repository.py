"""Repositorio de reglas de alerta."""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.core.db import SessionLocal


def _row_to_dict(r) -> dict:
    return {
        "id": r.id,
        "assetId": r.asset_id,
        "type": r.type,
        "direction": r.direction,
        "threshold": r.threshold,
        "indicator": r.indicator,
        "timeframe": r.timeframe,
        "channels": r.channels,
        "cooldownSeconds": r.cooldown_seconds,
        "enabled": r.enabled,
        "lastTriggeredAt": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
    }


async def list_rules(only_enabled: bool = False) -> list[dict]:
    query = "SELECT * FROM alert_rules"
    if only_enabled:
        query += " WHERE enabled = TRUE"
    query += " ORDER BY asset_id"
    async with SessionLocal() as session:
        rows = await session.execute(text(query))
        return [_row_to_dict(r) for r in rows]


async def create_rule(
    asset_id: str,
    rule_type: str,
    direction: str,
    threshold: float,
    indicator: str | None = None,
    timeframe: str = "1m",
    channels: str = "TELEGRAM",
    cooldown_seconds: int = 300,
) -> dict:
    rule_id = str(uuid.uuid4())
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO alert_rules
                    (id, asset_id, type, direction, threshold, indicator, timeframe,
                     channels, cooldown_seconds, enabled)
                VALUES
                    (:id, :asset_id, :type, :direction, :threshold, :indicator, :timeframe,
                     :channels, :cooldown, TRUE)
                """
            ),
            {
                "id": rule_id,
                "asset_id": asset_id,
                "type": rule_type,
                "direction": direction,
                "threshold": threshold,
                "indicator": indicator,
                "timeframe": timeframe,
                "channels": channels,
                "cooldown": cooldown_seconds,
            },
        )
        await session.commit()
    return {
        "id": rule_id,
        "assetId": asset_id,
        "type": rule_type,
        "direction": direction,
        "threshold": threshold,
        "indicator": indicator,
        "timeframe": timeframe,
        "channels": channels,
        "cooldownSeconds": cooldown_seconds,
        "enabled": True,
    }


async def delete_rule(rule_id: str) -> None:
    async with SessionLocal() as session:
        await session.execute(text("DELETE FROM alert_rules WHERE id = :id"), {"id": rule_id})
        await session.commit()


async def set_enabled(rule_id: str, enabled: bool) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE alert_rules SET enabled = :enabled WHERE id = :id"),
            {"id": rule_id, "enabled": enabled},
        )
        await session.commit()


async def mark_triggered(rule_id: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE alert_rules SET last_triggered_at = now() WHERE id = :id"),
            {"id": rule_id},
        )
        await session.commit()
