"""Tests de las métricas del dashboard (funciones puras)."""

import pytest

from app.modules.dashboard import metrics


def _candle(o, h, low, c):
    return {"open": o, "high": h, "low": low, "close": c}


# ----------------------------- change_percent -----------------------------

def test_change_percent_positive():
    candles = [_candle(100, 105, 99, 102), _candle(102, 110, 101, 110)]
    # De la apertura de la primera (100) al último cierre (110) = +10%
    assert metrics.change_percent(candles) == pytest.approx(10.0)


def test_change_percent_negative():
    candles = [_candle(100, 100, 90, 95), _candle(95, 96, 89, 90)]
    assert metrics.change_percent(candles) == pytest.approx(-10.0)


def test_change_percent_empty_is_none():
    assert metrics.change_percent([]) is None


def test_change_percent_zero_open_is_none():
    assert metrics.change_percent([_candle(0, 1, 0, 1)]) is None


# ----------------------------- high_low -----------------------------

def test_high_low():
    candles = [_candle(10, 15, 8, 12), _candle(12, 20, 11, 18)]
    high, low = metrics.high_low(candles)
    assert high == 20
    assert low == 8


def test_high_low_empty():
    assert metrics.high_low([]) == (None, None)


# ----------------------------- volatility -----------------------------

def test_volatility_zero_for_flat_series():
    candles = [_candle(10, 10, 10, 10) for _ in range(5)]
    assert metrics.volatility(candles) == pytest.approx(0.0)


def test_volatility_none_when_too_few():
    assert metrics.volatility([_candle(10, 10, 10, 10)]) is None


def test_volatility_positive_for_moving_series():
    candles = [_candle(10, 10, 10, 10), _candle(10, 11, 10, 11),
               _candle(11, 12, 10, 9), _candle(9, 10, 8, 10)]
    vol = metrics.volatility(candles)
    assert vol is not None and vol > 0


# ----------------------------- summarize -----------------------------

def test_summarize_uses_live_price_over_last_close():
    candles = [_candle(100, 105, 99, 102)]
    summary = metrics.summarize("btcusdt", candles, last_price=103.5)
    assert summary["symbol"] == "btcusdt"
    assert summary["price"] == 103.5  # prioriza el precio en vivo
    assert summary["high"] == 105
    assert summary["low"] == 99


def test_summarize_falls_back_to_last_close():
    candles = [_candle(100, 105, 99, 102)]
    summary = metrics.summarize("btcusdt", candles, last_price=None)
    assert summary["price"] == 102  # sin precio en vivo, usa el último cierre


def test_summarize_no_candles_no_price():
    summary = metrics.summarize("btcusdt", [], last_price=None)
    assert summary["price"] is None
    assert summary["changePercent"] is None


# ----------------------------- top_movers -----------------------------

def _summary(symbol, change):
    return {"symbol": symbol, "changePercent": change}


def test_top_movers_orders_gainers_and_losers():
    summaries = [
        _summary("a", 5.0),
        _summary("b", -3.0),
        _summary("c", 10.0),
        _summary("d", -8.0),
    ]
    movers = metrics.top_movers(summaries, limit=2)
    # Gainers ordenados de mayor a menor.
    assert [s["symbol"] for s in movers["gainers"]] == ["c", "a"]
    # Losers ordenados de menor (más negativo) a mayor.
    assert [s["symbol"] for s in movers["losers"]] == ["d", "b"]


def test_top_movers_ignores_none_change():
    summaries = [_summary("a", None), _summary("b", 5.0)]
    movers = metrics.top_movers(summaries)
    assert [s["symbol"] for s in movers["gainers"]] == ["b"]


def test_top_movers_empty():
    movers = metrics.top_movers([])
    assert movers == {"gainers": [], "losers": []}


# ----------------------------- most_volatile -----------------------------

def test_most_volatile_orders_desc():
    summaries = [
        {"symbol": "a", "volatility": 1.0},
        {"symbol": "b", "volatility": 5.0},
        {"symbol": "c", "volatility": None},
        {"symbol": "d", "volatility": 3.0},
    ]
    result = metrics.most_volatile(summaries, limit=2)
    assert [s["symbol"] for s in result] == ["b", "d"]
