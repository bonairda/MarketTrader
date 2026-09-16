"""Tests de la puntuación de riesgo."""

import pytest

from app.modules.signals import risk


def _candle(close, open_=None, high=None, low=None):
    o = open_ if open_ is not None else close
    return {
        "open": o,
        "high": high if high is not None else max(o, close),
        "low": low if low is not None else min(o, close),
        "close": close,
    }


def test_max_drawdown_none_when_too_few():
    assert risk.max_drawdown([_candle(10)]) is None


def test_max_drawdown_computes_worst_drop():
    # Sube a 100 y cae a 80 -> drawdown 20%.
    candles = [_candle(100), _candle(120), _candle(96)]
    dd = risk.max_drawdown(candles)
    assert dd == pytest.approx(20.0)  # (120-96)/120 = 20%


def test_score_low_for_flat_series():
    candles = [_candle(10) for _ in range(10)]
    result = risk.score(candles)
    assert result.score == 0
    assert result.level == "LOW"


def test_score_insufficient_data():
    result = risk.score([_candle(10)])
    assert result.level == "LOW"
    assert "Sin datos" in result.factors[0]


def test_score_high_for_volatile_series():
    # Serie muy movida -> volatilidad y drawdown altos -> riesgo alto.
    prices = [100, 130, 90, 140, 70, 150, 60]
    candles = [_candle(float(p)) for p in prices]
    result = risk.score(candles)
    assert result.score > 0
    assert result.level in ("MEDIUM", "HIGH")
    assert len(result.factors) >= 1
