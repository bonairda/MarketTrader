"""Repositorio de la watchlist. Define el universo de activos a seguir."""

from __future__ import annotations

from sqlalchemy import text

from app.core.db import SessionLocal


async def list_items() -> list[str]:
    async with SessionLocal() as session:
        rows = await session.execute(text("SELECT asset_id FROM watchlist_items ORDER BY added_at"))
        return [r.asset_id for r in rows]


async def add_item(asset_id: str, notes: str | None = None) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO watchlist_items (asset_id, notes)
                VALUES (:asset_id, :notes)
                ON CONFLICT (asset_id) DO NOTHING
                """
            ),
            {"asset_id": asset_id, "notes": notes},
        )
        await session.commit()


async def remove_item(asset_id: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("DELETE FROM watchlist_items WHERE asset_id = :asset_id"),
            {"asset_id": asset_id},
        )
        await session.commit()
