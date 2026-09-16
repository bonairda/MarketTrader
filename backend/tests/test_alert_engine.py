"""Tests del motor de alertas (cruce de precio + cooldown en Redis)."""

import fakeredis.aioredis
import pytest

from app.modules.alerts import engine as engine_module
from app.modules.alerts.engine import AlertEngine


@pytest.fixture
def fake_redis(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(engine_module, "get_redis", lambda: client)
    return client


@pytest.fixture
def fired(monkeypatch):
    """Captura las notificaciones enviadas y evita tocar Telegram / la BD."""
    messages: list[str] = []

    async def fake_send(text):
        messages.append(text)
        return True

    async def fake_mark(rule_id):
        return None

    monkeypatch.setattr(engine_module.dispatcher, "notify", fake_send)
    monkeypatch.setattr(engine_module.alerts_repo, "mark_triggered", fake_mark)
    return messages


def _rule(
    direction="ABOVE",
    threshold=100.0,
    cooldown=300,
    rid="r1",
    rule_type="PRICE_CROSS",
    indicator=None,
    timeframe="1m",
):
    return {
        "id": rid,
        "assetId": "btcusdt",
        "type": rule_type,
        "direction": direction,
        "threshold": threshold,
        "indicator": indicator,
        "timeframe": timeframe,
        "cooldownSeconds": cooldown,
    }


def _candle(close, open_=None):
    o = open_ if open_ is not None else close
    return {"open": o, "high": max(o, close), "low": min(o, close), "close": close}


async def test_no_fire_without_two_prices(fake_redis, fired):
    engine = AlertEngine()
    engine._rules_by_symbol = {"btcusdt": [_rule()]}
    # Primer tick: aún no hay precio anterior con el que comparar
    await engine.on_tick("btcusdt", 150)
    assert fired == []


async def test_fires_on_cross_above(fake_redis, fired):
    engine = AlertEngine()
    engine._rules_by_symbol = {"btcusdt": [_rule(direction="ABOVE", threshold=100)]}
    await engine.on_tick("btcusdt", 90)   # por debajo
    await engine.on_tick("btcusdt", 110)  # cruza por encima -> dispara
    assert len(fired) == 1
    assert "cruzado por encima de 100" in fired[0]


async def test_no_fire_if_stays_below(fake_redis, fired):
    engine = AlertEngine()
    engine._rules_by_symbol = {"btcusdt": [_rule(direction="ABOVE", threshold=100)]}
    await engine.on_tick("btcusdt", 90)
    await engine.on_tick("btcusdt", 95)  # sube pero no cruza
    assert fired == []


async def test_fires_on_cross_below(fake_redis, fired):
    engine = AlertEngine()
    engine._rules_by_symbol = {"btcusdt": [_rule(direction="BELOW", threshold=100)]}
    await engine.on_tick("btcusdt", 110)
    await engine.on_tick("btcusdt", 90)  # cruza por debajo
    assert len(fired) == 1
    assert "cruzado por debajo de 100" in fired[0]


async def test_cooldown_prevents_second_fire(fake_redis, fired):
    engine = AlertEngine()
    engine._rules_by_symbol = {"btcusdt": [_rule(threshold=100, cooldown=300)]}
    await engine.on_tick("btcusdt", 90)
    await engine.on_tick("btcusdt", 110)  # dispara y reserva cooldown
    await engine.on_tick("btcusdt", 90)   # baja
    await engine.on_tick("btcusdt", 110)  # vuelve a cruzar, pero en cooldown
    assert len(fired) == 1


async def test_zero_cooldown_allows_repeated_fires(fake_redis, fired):
    engine = AlertEngine()
    engine._rules_by_symbol = {"btcusdt": [_rule(threshold=100, cooldown=0)]}
    await engine.on_tick("btcusdt", 90)
    await engine.on_tick("btcusdt", 110)  # dispara
    await engine.on_tick("btcusdt", 90)
    await engine.on_tick("btcusdt", 110)  # dispara otra vez (sin cooldown)
    assert len(fired) == 2


async def test_no_rules_no_fire(fake_redis, fired):
    engine = AlertEngine()
    engine._rules_by_symbol = {}  # sin reglas para el símbolo
    await engine.on_tick("btcusdt", 90)
    await engine.on_tick("btcusdt", 110)
    assert fired == []


async def test_tick_ignores_non_price_cross_rules(fake_redis, fired):
    engine = AlertEngine()
    # Una regla PERCENT_CHANGE no debe evaluarse en on_tick.
    engine._rules_by_symbol = {"btcusdt": [_rule(rule_type="PERCENT_CHANGE", threshold=5)]}
    await engine.on_tick("btcusdt", 90)
    await engine.on_tick("btcusdt", 200)
    assert fired == []


# ----------------------------- PERCENT_CHANGE -----------------------------

async def test_percent_change_fires_above(fake_redis, fired, monkeypatch):
    engine = AlertEngine()
    engine._rules_by_symbol = {
        "btcusdt": [_rule(rule_type="PERCENT_CHANGE", direction="ABOVE", threshold=5)]
    }

    # Apertura 100, último cierre 110 -> +10% (supera el umbral de 5%).
    async def fake_bars(symbol, interval, limit=1440):
        return [_candle(100, open_=100), _candle(110)]

    monkeypatch.setattr(engine_module.bars, "get_bars", fake_bars)
    await engine.evaluate_candle_based()
    assert len(fired) == 1
    assert "subido" in fired[0]


async def test_percent_change_no_fire_below_threshold(fake_redis, fired, monkeypatch):
    engine = AlertEngine()
    engine._rules_by_symbol = {
        "btcusdt": [_rule(rule_type="PERCENT_CHANGE", direction="ABOVE", threshold=20)]
    }

    async def fake_bars(symbol, interval, limit=1440):
        return [_candle(100, open_=100), _candle(110)]  # +10% < 20%

    monkeypatch.setattr(engine_module.bars, "get_bars", fake_bars)
    await engine.evaluate_candle_based()
    assert fired == []


# ----------------------------- INDICATOR_CROSS -----------------------------

async def test_indicator_cross_rsi_above(fake_redis, fired, monkeypatch):
    engine = AlertEngine()
    engine._rules_by_symbol = {
        "btcusdt": [
            _rule(rule_type="INDICATOR_CROSS", indicator="rsi14", direction="ABOVE", threshold=70)
        ]
    }

    # Serie que sube fuerte: RSI alto (>70). Se necesitan dos evaluaciones para
    # detectar el cruce (primera guarda el valor, segunda compara).
    async def rising(symbol, interval, limit=500):
        return [_candle(float(i), open_=float(i)) for i in range(1, 40)]

    async def flat_low(symbol, interval, limit=500):
        # Serie plana tras una bajada -> RSI bajo.
        return [_candle(float(40 - i), open_=float(40 - i)) for i in range(1, 40)]

    # Primera evaluación con RSI bajo (siembra el "prev"), luego con RSI alto.
    monkeypatch.setattr(engine_module.bars, "get_bars", flat_low)
    await engine.evaluate_candle_based()  # guarda prev (RSI bajo), no dispara
    assert fired == []

    monkeypatch.setattr(engine_module.bars, "get_bars", rising)
    await engine.evaluate_candle_based()  # RSI cruza por encima de 70 -> dispara
    assert len(fired) == 1
    assert "RSI14" in fired[0]
