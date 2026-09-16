"""Tests de los indicadores técnicos (cálculo puro)."""

import pytest

from app.modules.market_data import indicators


# ----------------------------- SMA -----------------------------

def test_sma_basic():
    values = [1, 2, 3, 4, 5]
    result = indicators.sma(values, 3)
    # Los dos primeros no tienen ventana completa.
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(2.0)  # (1+2+3)/3
    assert result[3] == pytest.approx(3.0)  # (2+3+4)/3
    assert result[4] == pytest.approx(4.0)  # (3+4+5)/3


def test_sma_all_none_when_not_enough_data():
    assert indicators.sma([1, 2], 5) == [None, None]


def test_sma_invalid_period():
    with pytest.raises(ValueError):
        indicators.sma([1, 2, 3], 0)


# ----------------------------- EMA -----------------------------

def test_ema_seeds_with_sma():
    values = [1, 2, 3, 4, 5]
    result = indicators.ema(values, 3)
    assert result[0] is None
    assert result[1] is None
    # Semilla = SMA de los 3 primeros = 2.0
    assert result[2] == pytest.approx(2.0)
    # k = 2/(3+1) = 0.5; ema[3] = 4*0.5 + 2*0.5 = 3.0
    assert result[3] == pytest.approx(3.0)
    # ema[4] = 5*0.5 + 3*0.5 = 4.0
    assert result[4] == pytest.approx(4.0)


def test_ema_not_enough_data():
    assert indicators.ema([1, 2], 5) == [None, None]


# ----------------------------- RSI -----------------------------

def test_rsi_all_gains_is_100():
    values = [float(i) for i in range(1, 20)]  # siempre sube
    result = indicators.rsi(values, 14)
    # Sin pérdidas, el RSI es 100.
    assert result[14] == pytest.approx(100.0)


def test_rsi_none_until_period():
    values = [float(i) for i in range(1, 20)]
    result = indicators.rsi(values, 14)
    for i in range(14):
        assert result[i] is None


def test_rsi_not_enough_data():
    assert indicators.rsi([1, 2, 3], 14) == [None, None, None]


# ----------------------------- MACD -----------------------------

def test_macd_lengths_and_alignment():
    values = [float(i) for i in range(1, 60)]
    data = indicators.macd(values, fast=12, slow=26, signal=9)
    assert len(data["macd"]) == len(values)
    assert len(data["signal"]) == len(values)
    assert len(data["histogram"]) == len(values)
    # Antes de slow-1 no hay línea MACD.
    assert data["macd"][24] is None
    assert data["macd"][25] is not None


# ----------------------------- ATR -----------------------------

def test_atr_uses_true_range():
    highs = [10, 11, 12, 13]
    lows = [9, 10, 11, 12]
    closes = [9.5, 10.5, 11.5, 12.5]
    tr = indicators.true_range(highs, lows, closes)
    # TR[0] = high-low = 1; el resto también ~1 por el movimiento suave.
    assert tr[0] == pytest.approx(1.0)
    atr = indicators.atr(highs, lows, closes, period=2)
    assert atr[0] is None
    assert atr[1] is not None


# ----------------------------- Bollinger -----------------------------

def test_bollinger_constant_series_has_zero_width():
    values = [5.0] * 25
    data = indicators.bollinger(values, period=20, num_std=2.0)
    # Con serie constante, la desviación es 0 -> bandas iguales a la media.
    assert data["middle"][19] == pytest.approx(5.0)
    assert data["upper"][19] == pytest.approx(5.0)
    assert data["lower"][19] == pytest.approx(5.0)


def test_bollinger_bands_ordered():
    values = [float(i % 7) for i in range(40)]  # serie variable
    data = indicators.bollinger(values, period=20, num_std=2.0)
    i = 25
    assert data["lower"][i] <= data["middle"][i] <= data["upper"][i]


# ----------------------------- Returns -----------------------------

def test_returns_percentage():
    values = [100.0, 110.0, 99.0]
    result = indicators.returns(values)
    assert result[0] is None
    assert result[1] == pytest.approx(10.0)   # +10%
    assert result[2] == pytest.approx(-10.0)  # -10%


def test_returns_handles_zero_previous():
    values = [0.0, 5.0]
    result = indicators.returns(values)
    assert result[1] is None  # no se divide por cero
