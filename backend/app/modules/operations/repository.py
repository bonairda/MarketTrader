"""Acceso SQL al libro de operaciones.

Las mutaciones reciben una sesión externa para que el servicio pueda mantener
bloqueo, validación FIFO y escritura dentro de la misma transacción.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import JSON, bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal


def row_to_dict(row) -> dict:
    return {
        "id": row.id,
        "assetId": row.asset_id,
        "side": row.side,
        "tradeDate": row.trade_date,
        "executedAt": row.executed_at,
        "quantity": row.quantity,
        "unitPriceOriginal": row.unit_price_original,
        "grossAmountOriginal": row.gross_amount_original,
        "feesOriginal": row.fees_original,
        "currency": row.currency,
        "fxRateToEur": row.fx_rate_to_eur,
        "fxSource": row.fx_source,
        "source": row.source,
        "externalId": row.external_id,
        "notes": row.notes,
        "createdAt": row.created_at,
    }


async def list_operations(
    user_id: str,
    *,
    asset_id: str | None = None,
    side: str | None = None,
    year: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    clauses = ["user_id = :user_id"]
    params: dict = {"user_id": user_id, "limit": limit, "offset": offset}
    if asset_id:
        clauses.append("asset_id = :asset_id")
        params["asset_id"] = asset_id
    if side:
        clauses.append("side = :side")
        params["side"] = side
    if year:
        clauses.append("trade_date >= :year_start AND trade_date < :year_end")
        params["year_start"] = date(year, 1, 1)
        params["year_end"] = date(year + 1, 1, 1)
    query = (
        "SELECT * FROM operations WHERE "
        + " AND ".join(clauses)
        + " ORDER BY trade_date DESC, executed_at DESC NULLS LAST, created_at DESC, id DESC "
        + "LIMIT :limit OFFSET :offset"
    )
    async with SessionLocal() as session:
        rows = await session.execute(text(query), params)
        return [row_to_dict(row) for row in rows]


async def get_operation(user_id: str, operation_id: str) -> dict | None:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text(
                    "SELECT * FROM operations "
                    "WHERE id = :id AND user_id = :user_id"
                ),
                {"id": operation_id, "user_id": user_id},
            )
        ).first()
        return row_to_dict(row) if row else None


async def acquire_book_lock(
    session: AsyncSession, user_id: str, asset_id: str
) -> None:
    """Bloqueo transaccional por libro usuario/activo (PostgreSQL)."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"operations:{user_id}:{asset_id}"},
    )


async def list_book(
    session: AsyncSession,
    user_id: str,
    *,
    asset_id: str | None = None,
    through_year: int | None = None,
    exclude_id: str | None = None,
) -> list[dict]:
    clauses = ["user_id = :user_id"]
    params: dict = {"user_id": user_id}
    if asset_id:
        clauses.append("asset_id = :asset_id")
        params["asset_id"] = asset_id
    if through_year:
        clauses.append("trade_date < :year_end")
        params["year_end"] = date(through_year + 1, 1, 1)
    if exclude_id:
        clauses.append("id <> :exclude_id")
        params["exclude_id"] = exclude_id
    query = (
        "SELECT * FROM operations WHERE "
        + " AND ".join(clauses)
        + " ORDER BY trade_date ASC, executed_at ASC NULLS LAST, created_at ASC, id ASC"
    )
    rows = await session.execute(text(query), params)
    return [row_to_dict(row) for row in rows]


async def get_operation_for_update(
    session: AsyncSession, user_id: str, operation_id: str
) -> dict | None:
    row = (
        await session.execute(
            text(
                "SELECT * FROM operations "
                "WHERE id = :id AND user_id = :user_id FOR UPDATE"
            ),
            {"id": operation_id, "user_id": user_id},
        )
    ).first()
    return row_to_dict(row) if row else None


async def insert_operation(session: AsyncSession, operation: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO operations (
                id, user_id, asset_id, side, trade_date, executed_at, quantity,
                unit_price_original, gross_amount_original, fees_original,
                currency, fx_rate_to_eur, fx_source, source, external_id, notes
            ) VALUES (
                :id, :user_id, :asset_id, :side, :trade_date, :executed_at,
                :quantity, :unit_price_original, :gross_amount_original,
                :fees_original, :currency, :fx_rate_to_eur, :fx_source,
                :source, :external_id, :notes
            )
            """
        ),
        operation,
    )


async def delete_operation(session: AsyncSession, operation_id: str) -> None:
    await session.execute(
        text("DELETE FROM operations WHERE id = :id"), {"id": operation_id}
    )


async def insert_audit_log(
    session: AsyncSession,
    *,
    user_id: str,
    operation_id: str,
    action: str,
    payload: dict,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO operation_audit_log
                (id, user_id, operation_id, action, payload)
            VALUES (:id, :user_id, :operation_id, :action, :payload)
            """
        ).bindparams(bindparam("payload", type_=JSON)),
        {
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "operation_id": operation_id,
            "action": action,
            "payload": payload,
        },
    )


async def list_audit_log(
    user_id: str, *, limit: int = 200, offset: int = 0
) -> list[dict]:
    async with SessionLocal() as session:
        rows = await session.execute(
            text(
                """
                SELECT id, operation_id, action, payload, created_at
                FROM operation_audit_log
                WHERE user_id = :user_id
                ORDER BY created_at DESC, id DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"user_id": user_id, "limit": limit, "offset": offset},
        )
        return [
            {
                "id": row.id,
                "operationId": row.operation_id,
                "action": row.action,
                "payload": row.payload,
                "createdAt": row.created_at.isoformat(),
            }
            for row in rows
        ]
