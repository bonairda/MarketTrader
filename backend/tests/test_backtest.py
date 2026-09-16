"""Tests del motor de backtesting."""

import pytest

from app.modules.backtest import engine
from app.modules.backtest.engine import Trade


def _candle(close):
    return {"open": close, "high": close, "low": close, "close": close}


def test_trade_return_pct():
    t = Trade(entry_index=0, entry_price=100, exit_index=5, exit_price=110)
    assert t.return_pct == pytest.approx(10.0)
    losing = Trade(0, 100, 5, 80)
    assert losing.return_pct == pytest.approx(-20.0)


def test_trade_return_zero_entry():
    t = Trade(0, 0, 1, 50)
    assert t.return_pct == 0.0


def test_run_returns_empty_when_not_enough_candles():
    candles = [_candle(100) for _ in range(10)]  # <= warmup
    result = engine.run(candles)
    assert result.trades == 0
    assert result.total_return_pct == 0.0


def test_summarize_compounds_returns():
    # Dos operaciones: +10% y +10% -> retorno compuesto 1.1 * 1.1 - 1 = 21%.
    trades = [Trade(0, 100, 1, 110), Trade(2, 100, 3, 110)]
    result = engine._summarize(trades)
    assert result.trades == 2
    assert result.win_rate == pytest.approx(100.0)
    assert result.total_return_pct == pytest.approx(21.0)
    assert result.avg_return_pct == pytest.approx(10.0)


def test_summarize_win_rate_mixed():
    trades = [Trade(0, 100, 1, 110), Trade(2, 100, 3, 90)]  # +10%, -10%
    result = engine._summarize(trades)
    assert result.win_rate == pytest.approx(50.0)


def test_summarize_empty():
    result = engine._summarize([])
    assert result.trades == 0
    assert result.win_rate == 0.0


def test_max_drawdown_computes_worst_dip():
    # Curva de equity que sube a 1.2 y baja a 0.9 -> drawdown 25%.
    curve = [1.0, 1.2, 0.9, 1.0]
    dd = engine._max_drawdown(curve)
    assert dd == pytest.approx(25.0)  # (1.2-0.9)/1.2


def test_run_full_series_produces_result():
    # Serie larga y variada: el backtest debe ejecutarse sin errores y devolver
    # métricas coherentes (no verificamos operaciones concretas, sí la integridad).
    prices = [100 + (i % 10) - (i % 7) for i in range(200)]
    candles = [_candle(float(p)) for p in prices]
    result = engine.run(candles)
    assert result.trades >= 0
    assert -100 <= result.max_drawdown_pct <= 100
    assert 0 <= result.win_rate <= 100
