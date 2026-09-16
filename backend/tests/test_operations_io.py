"""Tests de import/export del libro de operaciones."""

import pytest

from app.core.errors import AppError
from app.modules.operations import io as operations_io


def test_parse_json_payload_maps_fields():
    content = (
        '{"operations": [{"assetId": "stock:AAPL", "side": "BUY", '
        '"tradeDate": "2025-01-01", "quantity": "10", "unitPriceOriginal": "100", '
        '"grossAmountOriginal": "1000", "currency": "USD", "externalId": "e1"}]}'
    )
    rows = operations_io.parse_import_payload(content, "json")
    assert rows[0]["asset_id"] == "stock:AAPL"
    assert rows[0]["external_id"] == "e1"
    assert rows[0]["source"] == "IMPORT"


def test_parse_csv_detects_semicolon_and_comma():
    csv_semicolon = "assetId;side;externalId\nbtcusdt;BUY;e1\n"
    csv_comma = "assetId,side,externalId\nbtcusdt,BUY,e2\n"
    assert operations_io.parse_import_payload(csv_semicolon, "csv")[0]["external_id"] == "e1"
    assert operations_io.parse_import_payload(csv_comma, "csv")[0]["external_id"] == "e2"


def test_parse_invalid_json_raises():
    with pytest.raises(AppError) as exc:
        operations_io.parse_import_payload("{not json", "json")
    assert exc.value.code == "INVALID_IMPORT"


def test_export_csv_has_bom_and_header():
    operations = [
        {
            "id": "op1",
            "assetId": "stock:AAPL",
            "side": "BUY",
            "tradeDate": "2025-01-01",
            "quantity": "10.000000000000",
            "grossAmountOriginal": "1000.000000000000",
            "currency": "USD",
        }
    ]
    csv_text = operations_io.export_csv(operations)
    assert csv_text.startswith("\ufeffid;assetId;side;")
    assert "stock:AAPL" in csv_text


async def test_import_skips_duplicates_and_requires_external_id(monkeypatch):
    async def fake_list(user_id, **kwargs):
        return [{"externalId": "existing"}]

    created: list[dict] = []

    async def fake_create(user_id, row):
        created.append(row)
        return {"id": "new"}

    monkeypatch.setattr(operations_io.service, "list_operations", fake_list)
    monkeypatch.setattr(operations_io.service, "create_operation", fake_create)

    rows = [
        {"external_id": "existing", "asset_id": "x", "source": "IMPORT"},  # duplicada
        {"external_id": "", "asset_id": "y", "source": "IMPORT"},  # sin id
        {"external_id": "new1", "asset_id": "z", "source": "IMPORT"},  # nueva
        {"external_id": "new1", "asset_id": "z", "source": "IMPORT"},  # dup en lote
    ]
    result = await operations_io.import_operations("user-a", rows)
    assert result["created"] == 1
    assert result["skipped"] == 2
    assert result["failed"] == 1
    assert len(created) == 1


async def test_import_dry_run_does_not_create(monkeypatch):
    async def fake_list(user_id, **kwargs):
        return []

    async def fake_prepare(row):
        return row

    def fake_validate(prepared):
        return prepared

    async def fail_create(user_id, row):  # pragma: no cover - no debe llamarse
        raise AssertionError("dry-run no debe crear")

    monkeypatch.setattr(operations_io.service, "list_operations", fake_list)
    monkeypatch.setattr(operations_io.service, "prepare_import_row", fake_prepare)
    monkeypatch.setattr(operations_io.service, "validate_prepared", fake_validate)
    monkeypatch.setattr(operations_io.service, "create_operation", fail_create)

    rows = [{"external_id": "e1", "asset_id": "x", "source": "IMPORT"}]
    result = await operations_io.import_operations("user-a", rows, dry_run=True)
    assert result["dryRun"] is True
    assert result["created"] == 1
