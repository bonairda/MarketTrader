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

    monkeypatch.setattr(engine_module.telegram, "send_message", fake_send)
    monkeypatch.setattr(engine_module.alerts_repo, "mark_triggered", fake_mark)
    return messages


def _rule(direction="ABOVE", threshold=100.0, cooldown=300, rid="r1"):
    return {
        "id": rid,
        "assetId": "btcusdt",
        "direction": direction,
        "threshold": threshold,
        "cooldownSeconds": cooldown,
    }


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
