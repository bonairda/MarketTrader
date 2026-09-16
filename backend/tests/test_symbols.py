"""Tests del enrutado y normalización de símbolos por proveedor."""

from app.providers import symbols
from app.providers.symbols import ProviderKind


def test_provider_for_crypto_by_default():
    assert symbols.provider_for("btcusdt") == ProviderKind.CRYPTO


def test_provider_for_stock_and_fx():
    assert symbols.provider_for("stock:AAPL") == ProviderKind.TWELVE_DATA
    assert symbols.provider_for("fx:EUR/USD") == ProviderKind.TWELVE_DATA


def test_to_provider_symbol_strips_prefix():
    assert symbols.to_provider_symbol("stock:AAPL") == "AAPL"
    assert symbols.to_provider_symbol("fx:EUR/USD") == "EUR/USD"
    assert symbols.to_provider_symbol("btcusdt") == "btcusdt"


def test_group_by_provider():
    grouped = symbols.group_by_provider(["btcusdt", "stock:AAPL", "ethusdt", "fx:EUR/USD"])
    assert grouped[ProviderKind.CRYPTO] == ["btcusdt", "ethusdt"]
    assert grouped[ProviderKind.TWELVE_DATA] == ["stock:AAPL", "fx:EUR/USD"]


def test_normalize_asset_id():
    assert symbols.normalize_asset_id("BTCUSDT") == "btcusdt"
    assert symbols.normalize_asset_id("Stock:aapl") == "stock:AAPL"
    assert symbols.normalize_asset_id("FX:eur/usd") == "fx:EUR/USD"
    assert symbols.normalize_asset_id("  ethusdt  ") == "ethusdt"
