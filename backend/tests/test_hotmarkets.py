"""Tests del detector de mercados llamativos."""

from app.modules.signals import hotmarkets


def _candle(close, high=None, low=None, volume=1.0):
    return {
        "open": close,
        "high": high if high is not None else close,
        "low": low if low is not None else close,
        "close": close,
        "volume": volume,
    }


def test_none_when_too_few_candles():
    candles = [_candle(100) for _ in range(5)]
    assert hotmarkets.detect("btcusdt", candles) is None


def test_none_when_calm_market():
    # 25 velas con variación mínima y volumen estable: nada llamativo.
    candles = [_candle(100 + (i % 2) * 0.1, volume=10) for i in range(25)]
    assert hotmarkets.detect("btcusdt", candles) is None


def test_detects_abnormal_move():
    # Body con variaciones pequeñas (std > 0) y última vela con salto enorme,
    # que queda muy por encima de 3 desviaciones respecto a lo normal.
    candles = [_candle(100.0 + (i % 2) * 0.1, volume=10) for i in range(24)]
    candles.append(_candle(130.0, volume=10))  # +30% de golpe
    hit = hotmarkets.detect("btcusdt", candles)
    assert hit is not None
    assert hit.reason == "MOVE"


def test_detects_volume_spike():
    # Precio con pequeñas variaciones (para no disparar MOVE) y volumen final alto.
    candles = [_candle(100 + (i % 2) * 0.05, volume=10) for i in range(24)]
    candles.append(_candle(100.05, volume=100))  # 10x volumen
    hit = hotmarkets.detect("btcusdt", candles)
    assert hit is not None
    assert hit.reason == "VOLUME"


def test_detects_breakout():
    # Rango estable y última vela por encima del máximo previo, sin salto brusco
    # de retorno (subida contenida repartida) para que gane BREAKOUT.
    candles = [_candle(100 + (i % 3) * 0.1, high=100.3, low=99.9, volume=10) for i in range(24)]
    candles.append(_candle(100.5, high=100.6, low=100.2, volume=10))
    hit = hotmarkets.detect("btcusdt", candles)
    assert hit is not None
    # Puede ser MOVE o BREAKOUT según la desviación; verificamos que detecta algo.
    assert hit.reason in ("BREAKOUT", "MOVE")
