"""Tests del servicio de eventos corporativos (repo y FX simulados)."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.modules.corporate import service


def test_serialize_dividend_computes_eur_and_net():
    event = {
        "id": "e1",
        "assetId": "stock:AAPL",
        "type": "DIVIDEND",
        "eventDate": date(2025, 3, 1),
        "grossAmountOriginal": Decimal("100"),
        "withholdingOriginal": Decimal("15"),
        "currency": "USD",
        "fxRateToEur": Decimal("0.9"),
        "ratio": None,
        "fxSource": "ECB",
        "externalId": None,
        "notes": None,
        "createdAt": None,
    }
    result = service.serialize_event(event)
    assert result["grossAmountEur"] == "90.00"
    assert result["withholdingEur"] == "13.50"
    assert result["netAmountEur"] == "76.50"


async def test_add_dividend_autofills_fx(monkeypatch):
    async def fake_rate(currency, on):
        return {"rate": "0.9", "source": "ECB", "effectiveDate": on.isoformat()}

    stored: list[dict] = []

    async def fake_insert(record):
        stored.append(record)

    async def fake_list(user_id, **kwargs):
        return []

    monkeypatch.setattr(service.fx_service, "get_rate_to_eur", fake_rate)
    monkeypatch.setattr(service.repository, "insert_event", fake_insert)
    monkeypatch.setattr(service.repository, "list_events", fake_list)

    result = await service.add_event(
        "user-a",
        {
            "asset_id": "stock:AAPL",
            "type": "DIVIDEND",
            "event_date": date(2025, 3, 1),
            "gross_amount_original": Decimal("100"),
            "withholding_original": Decimal("15"),
            "currency": "USD",
            "fx_rate_to_eur": None,
        },
    )
    assert stored[0]["fx_rate_to_eur"] == Decimal("0.9")
    assert result["netAmountEur"] == "76.50"


async def test_add_dividend_rejects_withholding_above_gross(monkeypatch):
    async def fake_rate(currency, on):  # pragma: no cover
        return {"rate": "1", "source": "ECB", "effectiveDate": on.isoformat()}

    monkeypatch.setattr(service.fx_service, "get_rate_to_eur", fake_rate)
    with pytest.raises(AppError) as exc:
        await service.add_event(
            "user-a",
            {
                "asset_id": "stock:AAPL",
                "type": "DIVIDEND",
                "event_date": date(2025, 3, 1),
                "gross_amount_original": Decimal("10"),
                "withholding_original": Decimal("20"),
                "currency": "EUR",
            },
        )
    assert exc.value.code == "INVALID_DIVIDEND"


async def test_add_split_requires_positive_ratio():
    with pytest.raises(AppError) as exc:
        await service.add_event(
            "user-a",
            {
                "asset_id": "stock:AAPL",
                "type": "SPLIT",
                "event_date": date(2025, 3, 1),
                "ratio": Decimal("0"),
            },
        )
    assert exc.value.code == "INVALID_SPLIT"


async def test_dividend_summary_totals(monkeypatch):
    async def fake_list(user_id, year):
        return [
            {
                "grossAmountOriginal": Decimal("100"),
                "withholdingOriginal": Decimal("15"),
                "fxRateToEur": Decimal("0.9"),
            },
            {
                "grossAmountOriginal": Decimal("50"),
                "withholdingOriginal": Decimal("5"),
                "fxRateToEur": Decimal("1"),
            },
        ]

    monkeypatch.setattr(service.repository, "list_dividends_for_year", fake_list)
    summary = await service.dividend_summary("user-a", 2025)
    assert summary["count"] == 2
    # 100*0.9 + 50*1 = 140 ; retención 15*0.9 + 5 = 18.5 ; neto 121.5
    assert summary["grossEur"] == "140.00"
    assert summary["withholdingEur"] == "18.50"
    assert summary["netEur"] == "121.50"
