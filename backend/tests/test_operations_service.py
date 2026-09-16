"""Tests de validación, aislamiento y exportación del módulo operations."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.core.errors import AppError, NotFoundError
from app.modules.operations import service
from app.modules.operations.fifo import build_tax_report


def _input(**overrides) -> dict:
    data = {
        "asset_id": "stock:AAPL",
        "side": "BUY",
        "trade_date": date(2025, 1, 1),
        "executed_at": None,
        "quantity": Decimal("2"),
        "unit_price_original": Decimal("10"),
        "gross_amount_original": Decimal("20"),
        "fees_original": Decimal("1"),
        "currency": "usd",
        "fx_rate_to_eur": Decimal("0.9"),
        "fx_source": "ecb",
        "source": "manual",
        "external_id": None,
        "notes": " prueba ",
    }
    data.update(overrides)
    return data


def _row(operation_id: str = "op1") -> dict:
    return {
        "id": operation_id,
        "assetId": "stock:AAPL",
        "side": "BUY",
        "tradeDate": date(2025, 1, 1),
        "executedAt": None,
        "quantity": Decimal("2"),
        "unitPriceOriginal": Decimal("10"),
        "grossAmountOriginal": Decimal("20"),
        "feesOriginal": Decimal("1"),
        "currency": "USD",
        "fxRateToEur": Decimal("0.9"),
        "fxSource": "ECB",
        "source": "MANUAL",
        "externalId": None,
        "notes": "prueba",
        "createdAt": datetime(2025, 1, 1, tzinfo=UTC),
    }


def _fifo_op(operation_id, side, trade_date, quantity, gross, fees="0"):
    return {
        "id": operation_id,
        "assetId": "stock:AAPL",
        "side": side,
        "tradeDate": date.fromisoformat(trade_date),
        "executedAt": None,
        "createdAt": datetime(2025, 1, 1, tzinfo=UTC),
        "quantity": Decimal(quantity),
        "grossAmountOriginal": Decimal(gross),
        "feesOriginal": Decimal(fees),
        "currency": "EUR",
        "fxRateToEur": Decimal("1"),
    }


def test_validate_normalizes_values_and_preserves_traceability():
    result = service._validate_input(_input())
    assert result["asset_id"] == "stock:AAPL"
    assert result["currency"] == "USD"
    assert result["fx_source"] == "ECB"
    assert result["source"] == "MANUAL"
    assert result["notes"] == "prueba"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("quantity", Decimal("0"), "INVALID_AMOUNTS"),
        ("fx_rate_to_eur", Decimal("0"), "INVALID_AMOUNTS"),
        ("fees_original", Decimal("21"), "INVALID_FEES"),
        ("currency", "?", "INVALID_CURRENCY"),
        ("gross_amount_original", Decimal("30"), "GROSS_MISMATCH"),
    ],
)
def test_validate_rejects_invalid_values(field, value, code):
    with pytest.raises(AppError) as exc:
        service._validate_input(_input(**{field: value}))
    assert exc.value.code == code
    assert exc.value.status_code == 422


def test_validate_rejects_future_date():
    with pytest.raises(AppError) as exc:
        service._validate_input(_input(trade_date=date(2999, 1, 1)))
    assert exc.value.code == "FUTURE_OPERATION"


def test_serialize_operation_uses_decimal_strings_and_eur_cash():
    serialized = service.serialize_operation(_row())
    assert serialized["quantity"] == "2.000000000000"
    assert serialized["grossAmountEur"] == "18.00"
    assert serialized["feesEur"] == "0.90"
    assert serialized["cashAmountEur"] == "18.90"  # BUY: bruto + comisión


async def test_list_operations_always_passes_user_id(monkeypatch):
    seen = {}

    async def fake_list(user_id, **filters):
        seen["user_id"] = user_id
        seen["filters"] = filters
        return [_row()]

    monkeypatch.setattr(service.repository, "list_operations", fake_list)
    result = await service.list_operations("user-a", year=2025, limit=10, offset=0)
    assert seen["user_id"] == "user-a"
    assert seen["filters"]["year"] == 2025
    assert result[0]["id"] == "op1"


async def test_get_operation_other_user_is_not_revealed(monkeypatch):
    async def fake_get(user_id, operation_id):
        assert user_id == "user-b"
        return None  # operación inexistente o de otro usuario: mismo resultado

    monkeypatch.setattr(service.repository, "get_operation", fake_get)
    with pytest.raises(NotFoundError):
        await service.get_operation("user-b", "operation-from-user-a")


def test_tax_report_serialization_and_csv_have_same_fifo_rows():
    raw = build_tax_report(
        [
            _fifo_op("b1", "BUY", "2024-01-01", "5", "500", fees="5"),
            _fifo_op("b2", "BUY", "2024-02-01", "5", "600"),
            _fifo_op("s1", "SELL", "2025-03-01", "8", "1040", fees="8"),
        ],
        2025,
    )
    report = service.serialize_tax_report(raw)
    csv_text = service.tax_report_csv(report)
    assert report["summary"]["matchedLots"] == 2
    assert report["summary"]["realizedGainEur"] == "167.00"
    assert csv_text.startswith("\ufeffejercicio;activo;")
    # Cabecera + dos emparejamientos FIFO.
    assert len(csv_text.splitlines()) == 3
    assert csv_text.count("stock:AAPL") == 2
    assert "Borrador informativo" in report["disclaimer"]


async def test_list_audit_log_always_filters_user(monkeypatch):
    seen = {}

    async def fake_list(user_id, *, limit, offset):
        seen.update(user_id=user_id, limit=limit, offset=offset)
        return []

    monkeypatch.setattr(service.repository, "list_audit_log", fake_list)
    assert await service.list_audit_log("user-a", limit=25, offset=5) == []
    assert seen == {"user_id": "user-a", "limit": 25, "offset": 5}


def test_report_totals_reconcile_with_rounded_disposals():
    raw = build_tax_report(
        [
            _fifo_op("b1", "BUY", "2024-01-01", "1", "1"),
            _fifo_op("s1", "SELL", "2025-01-01", "1", "1.004"),
            _fifo_op("b2", "BUY", "2025-01-02", "1", "1"),
            _fifo_op("s2", "SELL", "2025-01-03", "1", "1.004"),
            _fifo_op("b3", "BUY", "2025-01-04", "1", "1"),
            _fifo_op("s3", "SELL", "2025-01-05", "1", "1.004"),
        ],
        2025,
    )
    report = service.serialize_tax_report(raw)
    disposal_total = sum(Decimal(row["gainEur"]) for row in report["disposals"])
    asset_total = sum(Decimal(row["realizedGainEur"]) for row in report["assets"])
    assert Decimal(report["summary"]["realizedGainEur"]) == disposal_total == asset_total


async def test_list_operations_page_reports_has_more(monkeypatch):
    async def fake_list(user_id, **filters):
        return [_row(f"op{i}") for i in range(filters["limit"])]

    async def fake_count(user_id, **filters):
        return 130

    monkeypatch.setattr(service.repository, "list_operations", fake_list)
    monkeypatch.setattr(service.repository, "count_operations", fake_count)

    page = await service.list_operations_page("user-a", limit=50, offset=50)
    assert page["total"] == 130
    assert page["hasMore"] is True
    assert page["nextOffset"] == 100
    assert len(page["items"]) == 50


async def test_list_operations_page_last_page_has_no_next(monkeypatch):
    async def fake_list(user_id, **filters):
        return [_row("op1"), _row("op2")]

    async def fake_count(user_id, **filters):
        return 52

    monkeypatch.setattr(service.repository, "list_operations", fake_list)
    monkeypatch.setattr(service.repository, "count_operations", fake_count)

    page = await service.list_operations_page("user-a", limit=50, offset=50)
    assert page["hasMore"] is False
    assert page["nextOffset"] is None


async def test_create_operation_autofills_fx_from_ecb(monkeypatch):
    captured = {}

    async def fake_rate(currency, on):
        captured["currency"] = currency
        return {"rate": "0.9", "source": "ECB", "effectiveDate": on.isoformat()}

    monkeypatch.setattr(service.fx_service, "get_rate_to_eur", fake_rate)
    prepared = await service._resolve_fx_if_missing(
        {
            "currency": "USD",
            "trade_date": date(2025, 1, 1),
            "fx_rate_to_eur": None,
        }
    )
    assert prepared["fx_rate_to_eur"] == Decimal("0.9")
    assert prepared["fx_source"] == "ECB"
    assert captured["currency"] == "USD"


async def test_create_operation_fx_unavailable_raises(monkeypatch):
    async def no_rate(currency, on):
        return None

    monkeypatch.setattr(service.fx_service, "get_rate_to_eur", no_rate)
    with pytest.raises(AppError) as exc:
        await service._resolve_fx_if_missing(
            {"currency": "USD", "trade_date": date(2025, 1, 1), "fx_rate_to_eur": None}
        )
    assert exc.value.code == "FX_UNAVAILABLE"
