"""Repositorio de velas (PriceBar). Es lo ÚNICO que se persiste en la BD."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text

from app.core.db import SessionLocal


async def upsert_bar(
    asset_id: str,
    interval: str,
    open_time: datetime,
    o: float,
    h: float,
    l: float,
    c: float,
    volume: float | None = None,
) -> None:
    """Inserta o actualiza una vela cerrada."""
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO price_bars (asset_id, interval, open_time, open, high, low, close, volume)
                VALUES (:asset_id, :interval, :open_time, :open, :high, :low, :close, :volume)
                ON CONFLICT (asset_id, interval, open_time)
                DO UPDATE SET open=:open, high=:high, low=:low, close=:close, volume=:volume
                """
            ),
            {
                "asset_id": asset_id,
                "interval": interval,
                "open_time": open_time,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": volume,
            },
        )
        await session.commit()


async def get_bars(asset_id: str, interval: str, limit: int = 200) -> list[dict]:
    async with SessionLocal() as session:
        rows = await session.execute(
            text(
                """
                SELECT open_time, open, high, low, close, volume
                FROM price_bars
                WHERE asset_id = :asset_id AND interval = :interval
                ORDER BY open_time DESC
                LIMIT :limit
                """
            ),
            {"asset_id": asset_id, "interval": interval, "limit": limit},
        )
        return [
            {
                "openTime": r.open_time.isoformat(),
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ][::-1]  # orden cronológico ascendente
