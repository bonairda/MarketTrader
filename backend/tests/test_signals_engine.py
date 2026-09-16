"""Tests del motor de señales por reglas."""

from app.modules.signals.engine import SignalInputs, evaluate


def test_no_data_returns_hold():
    sig = evaluate(SignalInputs())
    assert sig.action == "HOLD"
    assert sig.confidence == 0


def test_strong_buy_when_all_bullish():
    # RSI sobreventa (+40) + tendencia alcista (+35) + MACD alcista (+25) = +100
    sig = evaluate(
        SignalInputs(rsi=25, sma20=110, sma50=100, macd=2, macd_signal=1)
    )
    assert sig.action == "BUY"
    assert sig.score == 100
    assert sig.confidence == 100
    assert any("sobreventa" in r for r in sig.rationale)


def test_strong_sell_when_all_bearish():
    sig = evaluate(
        SignalInputs(rsi=80, sma20=100, sma50=110, macd=1, macd_signal=2)
    )
    assert sig.action == "SELL"
    assert sig.score == 100


def test_watch_when_moderate_bias():
    # Solo MACD alcista (+25): net=25 -> no llega a BUY(50) pero >=20 -> WATCH.
    sig = evaluate(SignalInputs(macd=2, macd_signal=1))
    assert sig.action == "WATCH"
    assert sig.score == 25


def test_hold_when_conflicting():
    # RSI sobreventa (+40 bullish) vs tendencia bajista (-35 bearish): net=5 -> HOLD.
    sig = evaluate(SignalInputs(rsi=25, sma20=100, sma50=110))
    assert sig.action == "HOLD"


def test_rationale_is_populated():
    sig = evaluate(SignalInputs(rsi=50, sma20=110, sma50=100, macd=2, macd_signal=1))
    assert len(sig.rationale) >= 2  # al menos tendencia y MACD explicados
