"""Tests del agregador de velas de 1 minuto."""

from datetime import UTC, datetime

import pytest

from app.modules.market_data import aggregator as agg_module
from app.modules.market_data.aggregator import BarAggregator


@pytest.fixture
def captured(monkeypatch):
    """Captura las velas que el agregador intenta persistir (sin tocar la BD)."""
    saved: list[dict] = []

    async def fake_upsert(asset_id, interval, open_time, open_, high, low, close, volume=None):
        saved.append(
            {
                "asset_id": asset_id,
                "interval": interval,
                "open_time": open_time,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
            }
        )

    monkeypatch.setattr(agg_module.bars, "upsert_bar", fake_upsert)
    return saved


def _ms(minute: int, second: int = 0) -> int:
    """Timestamp en ms para un minuto epoch dado."""
    return (minute * 60 + second) * 1000


async def test_ohlc_within_same_minute(captured):
    agg = BarAggregator()
    # Todos en el minuto 100: open=10, high=15, low=8, close=12
    await agg.on_tick("btcusdt", 10, _ms(100, 1))
    await agg.on_tick("btcusdt", 15, _ms(100, 2))
    await agg.on_tick("btcusdt", 8, _ms(100, 3))
    await agg.on_tick("btcusdt", 12, _ms(100, 4))
    # Aún no se ha cerrado ninguna vela
    assert captured == []

    # Tick del minuto siguiente -> cierra la vela del minuto 100
    await agg.on_tick("btcusdt", 20, _ms(101, 0))
    assert len(captured) == 1
    bar = captured[0]
    assert bar["open"] == 10
    assert bar["high"] == 15
    assert bar["low"] == 8
    assert bar["close"] == 12
    assert bar["open_time"] == datetime.fromtimestamp(100 * 60, tz=UTC)


async def test_rollover_opens_new_candle(captured):
    agg = BarAggregator()
    await agg.on_tick("btcusdt", 10, _ms(100, 0))
    await agg.on_tick("btcusdt", 11, _ms(101, 0))  # cierra minuto 100, abre 101
    await agg.on_tick("btcusdt", 13, _ms(102, 0))  # cierra minuto 101
    assert len(captured) == 2
    assert captured[1]["open"] == 11
    assert captured[1]["close"] == 11


async def test_out_of_order_tick_ignored(captured):
    agg = BarAggregator()
    await agg.on_tick("btcusdt", 10, _ms(100, 10))
    # Tick más antiguo que la vela en curso: se ignora, no cierra ni abre nada
    await agg.on_tick("btcusdt", 99, _ms(99, 0))
    assert captured == []


async def test_flush_stale_closes_expired_candle(captured):
    agg = BarAggregator()
    await agg.on_tick("btcusdt", 10, _ms(100, 0))
    # "Ahora" está en el minuto 102 -> la vela del minuto 100 está vencida
    await agg.flush_stale(now_ms=_ms(102, 0))
    assert len(captured) == 1
    assert captured[0]["close"] == 10


async def test_flush_stale_keeps_current_candle(captured):
    agg = BarAggregator()
    await agg.on_tick("btcusdt", 10, _ms(100, 0))
    # "Ahora" sigue en el minuto 100 -> no se cierra
    await agg.flush_stale(now_ms=_ms(100, 30))
    assert captured == []


async def test_flush_all_persists_in_progress(captured):
    agg = BarAggregator()
    await agg.on_tick("btcusdt", 10, _ms(100, 0))
    await agg.on_tick("ethusdt", 5, _ms(100, 0))
    await agg.flush_all()
    assert len(captured) == 2
    symbols = {b["asset_id"] for b in captured}
    assert symbols == {"btcusdt", "ethusdt"}
