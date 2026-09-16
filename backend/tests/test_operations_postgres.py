"""Integración PostgreSQL real: migración, ownership, auditoría y concurrencia.

Solo se ejecuta cuando RUN_DB_TESTS=1 (CI con Timescale/PostgreSQL).
"""

import asyncio
import os
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.errors import AppError
from app.modules.operations import service

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Requiere PostgreSQL migrado"
)


def _input(side: str, quantity: str, gross: str, external_id: str) -> dict:
    return {
        "asset_id": "stock:AAPL",
        "side": side,
        "trade_date": date(2025, 1, 1) if side == "BUY" else date(2025, 2, 1),
        "executed_at": None,
        "quantity": Decimal(quantity),
        "unit_price_original": Decimal(gross) / Decimal(quantity),
        "gross_amount_original": Decimal(gross),
        "fees_original": Decimal("0"),
        "currency": "EUR",
        "fx_rate_to_eur": Decimal("1"),
        "fx_source": "USER",
        "source": "TEST",
        "external_id": external_id,
        "notes": None,
    }


async def _create_user(user_id: str, email: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO users (id, email, hashed_password, role, is_active)
                VALUES (:id, :email, 'test-only', 'OWNER', TRUE)
                """
            ),
            {"id": user_id, "email": email},
        )
        await session.commit()


async def _cleanup(user_ids: list[str]) -> None:
    params = {"user_a": user_ids[0], "user_b": user_ids[1]}
    condition = "user_id IN (:user_a, :user_b)"
    async with SessionLocal() as session:
        await session.execute(
            text(f"DELETE FROM operation_audit_log WHERE {condition}"), params
        )
        await session.execute(text(f"DELETE FROM operations WHERE {condition}"), params)
        await session.execute(
            text("DELETE FROM users WHERE id IN (:user_a, :user_b)"), params
        )
        await session.commit()


async def test_operations_are_isolated_audited_and_concurrency_safe():
    suffix = uuid.uuid4().hex
    user_a = f"test-a-{suffix}"
    user_b = f"test-b-{suffix}"
    await _create_user(user_a, f"a-{suffix}@example.com")
    await _create_user(user_b, f"b-{suffix}@example.com")
    try:
        buy_a = await service.create_operation(
            user_a, _input("BUY", "10", "100", f"buy-a-{suffix}")
        )
        await service.create_operation(
            user_b, _input("BUY", "3", "30", f"buy-b-{suffix}")
        )
        assert [row["id"] for row in await service.list_operations(user_a)] == [
            buy_a["id"]
        ]
        assert len(await service.list_operations(user_b)) == 1

        # Dos ventas de 8 compiten por un saldo de 10: el lock obliga a que solo
        # una confirme; la otra ve saldo 2 y devuelve 409.
        results = await asyncio.gather(
            service.create_operation(
                user_a, _input("SELL", "8", "120", f"sell-1-{suffix}")
            ),
            service.create_operation(
                user_a, _input("SELL", "8", "120", f"sell-2-{suffix}")
            ),
            return_exceptions=True,
        )
        successes = [result for result in results if isinstance(result, dict)]
        failures = [result for result in results if isinstance(result, AppError)]
        assert len(successes) == 1
        assert len(failures) == 1
        assert failures[0].code == "INSUFFICIENT_HOLDINGS"

        audit = await service.list_audit_log(user_a)
        assert [event["action"] for event in audit].count("CREATE") == 2
        assert all(event["payload"]["assetId"] == "stock:AAPL" for event in audit)

        await service.delete_operation(user_a, successes[0]["id"])
        audit = await service.list_audit_log(user_a)
        assert any(event["action"] == "DELETE" for event in audit)
    finally:
        await _cleanup([user_a, user_b])
