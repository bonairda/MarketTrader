"""Tests del parser de mensajes del WebSocket de Binance."""

import json

from app.providers.binance import BinanceProvider


def test_parse_valid_trade_message():
    raw = json.dumps({"s": "BTCUSDT", "p": "12345.67", "T": 1700000000000})
    tick = BinanceProvider._parse(raw)
    assert tick is not None
    assert tick.symbol == "btcusdt"  # se normaliza a minúsculas
    assert tick.price == 12345.67
    assert tick.timestamp_ms == 1700000000000


def test_parse_ignores_control_message():
    # Mensaje sin los campos de trade (p. ej. respuesta a suscripción).
    raw = json.dumps({"result": None, "id": 1})
    assert BinanceProvider._parse(raw) is None


def test_parse_ignores_invalid_json():
    assert BinanceProvider._parse("no-es-json") is None


def test_parse_ignores_non_numeric_price():
    raw = json.dumps({"s": "BTCUSDT", "p": "abc", "T": 1700000000000})
    assert BinanceProvider._parse(raw) is None


def test_parse_kline_maps_fields():
    # Formato Binance: [openTime, open, high, low, close, volume, ...]
    row = [1700000000000, "10.0", "12.5", "9.0", "11.0", "123.4", 1700000059999]
    bar = BinanceProvider._parse_kline("BTCUSDT", row)
    assert bar.symbol == "btcusdt"
    assert bar.open_time_ms == 1700000000000
    assert bar.open == 10.0
    assert bar.high == 12.5
    assert bar.low == 9.0
    assert bar.close == 11.0
    assert bar.volume == 123.4


def test_is_valid_kline():
    assert BinanceProvider._is_valid_kline([1, 2, 3, 4, 5, 6]) is True
    assert BinanceProvider._is_valid_kline([1, 2, 3]) is False
    assert BinanceProvider._is_valid_kline("not-a-list") is False
