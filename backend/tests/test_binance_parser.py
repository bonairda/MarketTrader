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
