"""Repositorio de la watchlist. Define el universo de activos a seguir.

Cada usuario tiene su propia watchlist (filtrada por `user_id`). El worker de
ingestión, en cambio, necesita la UNIÓN de todas las watchlists (una sola
ingestión sirve a todos los usuarios): para eso está `list_all_symbols`.
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.db import SessionLocal
from app.modules.watchlists.events import notify_watchlist_changed


async def list_items(user_id: str) -> list[str]:
    """Símbolos de la watchlist de un usuario concreto."""
    async with SessionLocal() as session:
        rows = await session.execute(
            text(
                "SELECT asset_id FROM watchlist_items "
                "WHERE user_id = :user_id ORDER BY added_at"
            ),
            {"user_id": user_id},
        )
        return [r.asset_id for r in rows]


async def list_all_symbols() -> list[str]:
    """Unión (sin duplicados) de todas las watchlists. Uso del worker/ingestión."""
    async with SessionLocal() as session:
        rows = await session.execute(
            text("SELECT DISTINCT asset_id FROM watchlist_items ORDER BY asset_id")
        )
        return [r.asset_id for r in rows]


async def add_item(user_id: str, asset_id: str, notes: str | None = None) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO watchlist_items (user_id, asset_id, notes)
                VALUES (:user_id, :asset_id, :notes)
                ON CONFLICT (user_id, asset_id) DO NOTHING
                """
            ),
            {"user_id": user_id, "asset_id": asset_id, "notes": notes},
        )
        await session.commit()
    await notify_watchlist_changed()


async def remove_item(user_id: str, asset_id: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                "DELETE FROM watchlist_items "
                "WHERE user_id = :user_id AND asset_id = :asset_id"
            ),
            {"user_id": user_id, "asset_id": asset_id},
        )
        await session.commit()
    await notify_watchlist_changed()
