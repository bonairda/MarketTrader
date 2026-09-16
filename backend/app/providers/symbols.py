"""Enrutado de símbolos por prefijo a su proveedor.

Convención de `asset_id`:
  - Cripto (Binance): sin prefijo, p. ej. "btcusdt".
  - Acciones (Twelve Data): "stock:AAPL".
  - Forex (Twelve Data): "fx:EUR/USD".

Este módulo decide a qué proveedor pertenece cada símbolo y traduce el
`asset_id` interno al símbolo que espera la API del proveedor.
"""

from __future__ import annotations

from enum import Enum

STOCK_PREFIX = "stock:"
FX_PREFIX = "fx:"


class ProviderKind(str, Enum):
    CRYPTO = "crypto"
    TWELVE_DATA = "twelve_data"


def provider_for(asset_id: str) -> ProviderKind:
    """Devuelve el proveedor que corresponde a un asset_id."""
    if asset_id.startswith(STOCK_PREFIX) or asset_id.startswith(FX_PREFIX):
        return ProviderKind.TWELVE_DATA
    return ProviderKind.CRYPTO


def to_provider_symbol(asset_id: str) -> str:
    """Traduce el asset_id interno al símbolo que espera el proveedor.

    - "stock:AAPL" -> "AAPL"
    - "fx:EUR/USD" -> "EUR/USD"
    - "btcusdt"    -> "btcusdt" (cripto, sin cambios)
    """
    if asset_id.startswith(STOCK_PREFIX):
        return asset_id[len(STOCK_PREFIX):]
    if asset_id.startswith(FX_PREFIX):
        return asset_id[len(FX_PREFIX):]
    return asset_id


def group_by_provider(asset_ids: list[str]) -> dict[ProviderKind, list[str]]:
    """Agrupa una lista de asset_ids por su proveedor."""
    grouped: dict[ProviderKind, list[str]] = {}
    for asset_id in asset_ids:
        grouped.setdefault(provider_for(asset_id), []).append(asset_id)
    return grouped


def normalize_asset_id(raw: str) -> str:
    """Normaliza el asset_id que llega de la API a un formato canónico.

    - Cripto: todo en minúsculas ("BTCUSDT" -> "btcusdt").
    - Acciones: prefijo en minúsculas + ticker en MAYÚSCULAS ("Stock:aapl" -> "stock:AAPL").
    - Forex: prefijo en minúsculas + par en MAYÚSCULAS ("FX:eur/usd" -> "fx:EUR/USD").
    """
    trimmed = raw.strip()
    lower = trimmed.lower()
    if lower.startswith(STOCK_PREFIX):
        return STOCK_PREFIX + trimmed[len(STOCK_PREFIX):].upper()
    if lower.startswith(FX_PREFIX):
        return FX_PREFIX + trimmed[len(FX_PREFIX):].upper()
    return lower
