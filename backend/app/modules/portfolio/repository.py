"""Repositorio de posiciones de cartera (simulada)."""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.core.db import SessionLocal


def _row_to_dict(r) -> dict:
    return {
        "id": r.id,
        "assetId": r.asset_id,
        "quantity": r.quantity,
        "averagePrice": r.average_price,
        "openedAt": r.opened_at.isoformat() if r.opened_at else None,
    }


async def list_positions() -> list[dict]:
    async with SessionLocal() as session:
        rows = await session.execute(text("SELECT * FROM positions ORDER BY opened_at"))
        return [_row_to_dict(r) for r in rows]


async def add_position(asset_id: str, quantity: float, average_price: float) -> dict:
    position_id = str(uuid.uuid4())
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO positions (id, asset_id, quantity, average_price)
                VALUES (:id, :asset_id, :quantity, :average_price)
                """
            ),
            {
                "id": position_id,
                "asset_id": asset_id,
                "quantity": quantity,
                "average_price": average_price,
            },
        )
        await session.commit()
    return {
        "id": position_id,
        "assetId": asset_id,
        "quantity": quantity,
        "averagePrice": average_price,
    }


async def delete_position(position_id: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("DELETE FROM positions WHERE id = :id"), {"id": position_id}
        )
        await session.commit()
