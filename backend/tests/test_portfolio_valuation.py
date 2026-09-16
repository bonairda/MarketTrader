"""Tests de la valoración de cartera (funciones puras)."""

import pytest

from app.modules.portfolio import valuation


def test_value_position_with_profit():
    v = valuation.value_position(quantity=2, average_price=100, current_price=120)
    assert v["cost"] == 200
    assert v["marketValue"] == 240
    assert v["pnl"] == 40
    assert v["pnlPercent"] == pytest.approx(20.0)


def test_value_position_with_loss():
    v = valuation.value_position(quantity=1, average_price=100, current_price=90)
    assert v["pnl"] == -10
    assert v["pnlPercent"] == pytest.approx(-10.0)


def test_value_position_without_price():
    v = valuation.value_position(quantity=1, average_price=100, current_price=None)
    assert v["cost"] == 100
    assert v["marketValue"] is None
    assert v["pnl"] is None
    assert v["pnlPercent"] is None


def test_summarize_totals():
    positions = [
        valuation.value_position(1, 100, 110),  # cost 100, value 110, pnl +10
        valuation.value_position(2, 50, 60),     # cost 100, value 120, pnl +20
    ]
    summary = valuation.summarize(positions)
    assert summary["totalCost"] == 200
    assert summary["totalValue"] == 230
    assert summary["totalPnl"] == 30
    assert summary["totalPnlPercent"] == pytest.approx(15.0)
    assert summary["positions"] == 2


def test_summarize_ignores_unpriced_in_value():
    positions = [
        valuation.value_position(1, 100, 110),     # priced
        valuation.value_position(1, 100, None),    # sin precio
    ]
    summary = valuation.summarize(positions)
    # El coste total sí incluye ambas; el valor solo la que tiene precio.
    assert summary["totalCost"] == 200
    assert summary["totalValue"] == 110
    assert summary["totalPnl"] == 10
