"""Acceso SQL a eventos corporativos, aislado por usuario."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text

from app.core.db import SessionLocal


def _row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "assetId": row.asset_id,
        "type": row.type,
        "eventDate": row.event_date,
        "grossAmountOriginal": row.gross_amount_original,
        "withholdingOriginal": row.withholding_original,
        "currency": row.currency,
        "fxRateToEur": row.fx_rate_to_eur,
        "ratio": row.ratio,
        "fxSource": row.fx_source,
        "externalId": row.external_id,
        "notes": row.notes,
        "createdAt": row.created_at,
    }


async def list_events(
    user_id: str, *, year: int | None = None, limit: int = 200, offset: int = 0
) -> list[dict]:
    clauses = ["user_id = :user_id"]
    params: dict = {"user_id": user_id, "limit": limit, "offset": offset}
    if year:
        clauses.append("event_date >= :start AND event_date < :end")
        params["start"] = date(year, 1, 1)
        params["end"] = date(year + 1, 1, 1)
    query = (
        "SELECT * FROM corporate_events WHERE "
        + " AND ".join(clauses)
        + " ORDER BY event_date DESC, id DESC LIMIT :limit OFFSET :offset"
    )
    async with SessionLocal() as session:
        rows = await session.execute(text(query), params)
        return [_row_to_dict(r) for r in rows]


async def list_dividends_for_year(user_id: str, year: int) -> list[dict]:
    async with SessionLocal() as session:
        rows = await session.execute(
            text(
                "SELECT * FROM corporate_events "
                "WHERE user_id = :user_id AND type = 'DIVIDEND' "
                "AND event_date >= :start AND event_date < :end "
                "ORDER BY event_date"
            ),
            {"user_id": user_id, "start": date(year, 1, 1), "end": date(year + 1, 1, 1)},
        )
        return [_row_to_dict(r) for r in rows]


async def insert_event(event: dict) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO corporate_events (
                    id, user_id, asset_id, type, event_date,
                    gross_amount_original, withholding_original, currency,
                    fx_rate_to_eur, ratio, fx_source, external_id, notes
                ) VALUES (
                    :id, :user_id, :asset_id, :type, :event_date,
                    :gross_amount_original, :withholding_original, :currency,
                    :fx_rate_to_eur, :ratio, :fx_source, :external_id, :notes
                )
                """
            ),
            event,
        )
        await session.commit()


async def delete_event(user_id: str, event_id: str) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            text("DELETE FROM corporate_events WHERE id = :id AND user_id = :user_id"),
            {"id": event_id, "user_id": user_id},
        )
        await session.commit()
        return result.rowcount or 0
