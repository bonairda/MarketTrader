"""Tests del motor FIFO fiscal puro."""

from datetime import date, datetime, UTC
from decimal import Decimal

import pytest

from app.modules.operations.fifo import (
    InsufficientHoldingsError,
    build_tax_report,
    calculate_fifo,
)


def _op(
    operation_id: str,
    side: str,
    trade_date: str,
    quantity: str,
    gross: str,
    *,
    asset: str = "stock:AAPL",
    fees: str = "0",
    fx: str = "1",
    currency: str = "EUR",
    executed_at: str | None = None,
) -> dict:
    return {
        "id": operation_id,
        "assetId": asset,
        "side": side,
        "tradeDate": date.fromisoformat(trade_date),
        "executedAt": executed_at,
        "createdAt": datetime(2025, 1, 1, tzinfo=UTC),
        "quantity": Decimal(quantity),
        "grossAmountOriginal": Decimal(gross),
        "feesOriginal": Decimal(fees),
        "currency": currency,
        "fxRateToEur": Decimal(fx),
    }


def test_single_buy_and_partial_sell_includes_both_fees():
    result = calculate_fifo(
        [
            _op("b1", "BUY", "2024-01-10", "10", "1000", fees="10"),
            _op("s1", "SELL", "2025-03-01", "4", "600", fees="6"),
        ]
    )
    assert len(result.disposals) == 1
    disposal = result.disposals[0]
    assert disposal["proceedsEur"] == Decimal("594")
    assert disposal["acquisitionCostEur"] == Decimal("404")
    assert disposal["gainEur"] == Decimal("190")
    assert result.open_lots[0]["remainingQuantity"] == Decimal("6")
    assert result.open_lots[0]["costEur"] == Decimal("606")


def test_sell_consumes_oldest_lots_and_splits_sale_fee_proportionally():
    result = calculate_fifo(
        [
            _op("b1", "BUY", "2024-01-01", "5", "500", fees="5"),
            _op("b2", "BUY", "2024-02-01", "5", "600"),
            _op("s1", "SELL", "2025-01-01", "8", "1040", fees="8"),
        ]
    )
    assert [d["buyOperationId"] for d in result.disposals] == ["b1", "b2"]
    assert [d["matchedQuantity"] for d in result.disposals] == [
        Decimal("5"),
        Decimal("3"),
    ]
    assert result.disposals[0]["gainEur"] == Decimal("140")
    assert result.disposals[1]["gainEur"] == Decimal("27")
    assert result.open_lots[0]["buyOperationId"] == "b2"
    assert result.open_lots[0]["remainingQuantity"] == Decimal("2")


def test_different_fx_rates_are_applied_at_each_operation_date():
    result = calculate_fifo(
        [
            _op(
                "b1",
                "BUY",
                "2024-01-01",
                "1",
                "100",
                fees="1",
                fx="0.9",
                currency="USD",
            ),
            _op(
                "s1",
                "SELL",
                "2025-01-01",
                "1",
                "120",
                fees="2",
                fx="0.8",
                currency="USD",
            ),
        ]
    )
    disposal = result.disposals[0]
    assert disposal["acquisitionCostEur"] == Decimal("90.9")
    assert disposal["proceedsEur"] == Decimal("94.4")
    assert disposal["gainEur"] == Decimal("3.5")
    assert disposal["saleFxRateToEur"] == Decimal("0.8")
    assert disposal["acquisitionFxRateToEur"] == Decimal("0.9")


def test_sell_without_enough_previous_holdings_is_rejected():
    with pytest.raises(InsufficientHoldingsError) as exc:
        calculate_fifo(
            [
                _op("b1", "BUY", "2025-01-01", "2", "20"),
                _op("s1", "SELL", "2025-01-02", "3", "45"),
            ]
        )
    assert exc.value.required == Decimal("3")
    assert exc.value.available == Decimal("2")


def test_sell_before_buy_is_rejected_even_if_later_balance_is_positive():
    with pytest.raises(InsufficientHoldingsError):
        calculate_fifo(
            [
                _op("s1", "SELL", "2025-01-01", "1", "10"),
                _op("b1", "BUY", "2025-01-02", "1", "10"),
            ]
        )


def test_same_day_uses_executed_at_before_creation_order():
    result = calculate_fifo(
        [
            _op(
                "s1",
                "SELL",
                "2025-01-01",
                "1",
                "15",
                executed_at="2025-01-01T11:00:00Z",
            ),
            _op(
                "b1",
                "BUY",
                "2025-01-01",
                "1",
                "10",
                executed_at="2025-01-01T10:00:00Z",
            ),
        ]
    )
    assert result.disposals[0]["gainEur"] == Decimal("5")


def test_assets_have_independent_fifo_books():
    result = calculate_fifo(
        [
            _op("a-buy", "BUY", "2025-01-01", "1", "10"),
            _op("btc-buy", "BUY", "2025-01-01", "2", "40", asset="btcusdt"),
            _op("a-sell", "SELL", "2025-02-01", "1", "12"),
        ]
    )
    assert len(result.disposals) == 1
    assert result.open_lots[0]["assetId"] == "btcusdt"


def test_tax_report_uses_prior_year_buys_and_only_current_year_sales():
    report = build_tax_report(
        [
            _op("b1", "BUY", "2023-01-01", "10", "1000"),
            _op("s-old", "SELL", "2024-06-01", "2", "240"),
            _op("s-year", "SELL", "2025-06-01", "3", "450"),
            _op("s-future", "SELL", "2026-06-01", "1", "180"),
        ],
        2025,
    )
    assert report["summary"]["sellOperations"] == 1
    assert report["summary"]["matchedLots"] == 1
    assert report["summary"]["proceedsEur"] == Decimal("450")
    assert report["summary"]["acquisitionCostEur"] == Decimal("300")
    assert report["summary"]["realizedGainEur"] == Decimal("150")
    assert report["disposals"][0]["sellOperationId"] == "s-year"
    # El estado abierto se calcula a cierre de 2025: 10 - 2 - 3 = 5.
    assert report["openLots"][0]["remainingQuantity"] == Decimal("5")


def test_decimal_precision_does_not_create_negative_residue():
    result = calculate_fifo(
        [
            _op("b1", "BUY", "2025-01-01", "0.3", "0.3"),
            _op("s1", "SELL", "2025-01-02", "0.1", "0.2"),
            _op("s2", "SELL", "2025-01-03", "0.2", "0.4"),
        ]
    )
    assert result.open_lots == []
    assert sum((d["matchedQuantity"] for d in result.disposals), Decimal("0")) == Decimal(
        "0.3"
    )
