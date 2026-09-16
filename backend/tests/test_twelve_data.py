"""Tests del parser de Twelve Data (respuestas de /price y /time_series)."""

from app.providers.twelve_data import TwelveDataProvider


def test_parse_prices_single_symbol():
    # Con un solo símbolo, Twelve Data devuelve {"price": "1.23"}.
    result = TwelveDataProvider._parse_prices(["AAPL"], {"price": "150.25"})
    assert result == {"AAPL": 150.25}


def test_parse_prices_multiple_symbols():
    data = {
        "AAPL": {"price": "150.25"},
        "MSFT": {"price": "410.10"},
    }
    result = TwelveDataProvider._parse_prices(["AAPL", "MSFT"], data)
    assert result == {"AAPL": 150.25, "MSFT": 410.10}


def test_parse_prices_ignores_missing_or_invalid():
    data = {"AAPL": {"price": "abc"}, "MSFT": {}}
    result = TwelveDataProvider._parse_prices(["AAPL", "MSFT"], data)
    assert result == {}


def test_parse_bar_maps_fields():
    row = {
        "datetime": "2024-01-01 12:34:00",
        "open": "10.0",
        "high": "12.0",
        "low": "9.0",
        "close": "11.0",
        "volume": "1000",
    }
    bar = TwelveDataProvider._parse_bar("stock:AAPL", row)
    assert bar is not None
    assert bar.symbol == "stock:AAPL"
    assert bar.open == 10.0
    assert bar.high == 12.0
    assert bar.low == 9.0
    assert bar.close == 11.0
    assert bar.volume == 1000.0


def test_parse_bar_handles_missing_volume():
    row = {
        "datetime": "2024-01-01 12:34:00",
        "open": "1", "high": "2", "low": "1", "close": "2", "volume": "",
    }
    bar = TwelveDataProvider._parse_bar("fx:EUR/USD", row)
    assert bar is not None
    assert bar.volume is None


def test_parse_bar_invalid_returns_none():
    assert TwelveDataProvider._parse_bar("stock:AAPL", {"datetime": "bad"}) is None
