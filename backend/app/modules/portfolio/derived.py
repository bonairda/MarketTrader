"""Cartera derivada del libro fiscal, valorada en EUR.

A diferencia de la cartera manual (`positions`), esta se calcula a partir de los
lotes FIFO abiertos del libro de operaciones. El coste ya está en EUR (calculado
por el motor FIFO). El valor de mercado se estima con el precio en vivo,
convertido a EUR con el tipo de cambio del BCE cuando la cotización no es en EUR.

Todo se opera en Decimal; la cuantización se hace solo al serializar.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.core.db import SessionLocal
from app.modules.fx import service as fx_service
from app.modules.market_data import live
from app.modules.operations import repository as operations_repository
from app.modules.operations.fifo import calculate_fifo

_MONEY = Decimal("0.01")
_QUANTITY = Decimal("0.000000000001")

# Divisa de cotización asumida por proveedor/prefijo del asset_id.
_STOCK_PREFIX = "stock:"
_FX_PREFIX = "fx:"


def _money(value: Decimal) -> str:
    return format(value.quantize(_MONEY, rounding=ROUND_HALF_UP), "f")


def _fixed(value: Decimal) -> str:
    return format(value.quantize(_QUANTITY, rounding=ROUND_HALF_UP), "f")


def _quote_currency(asset_id: str) -> str:
    """Divisa en la que cotiza el precio en vivo del activo.

    Cripto (btcusdt) cotiza en USDT; acciones/forex vía Twelve Data se asumen en
    USD salvo forex, cuyo par ya expresa la divisa cotizada.
    """
    if asset_id.startswith(_STOCK_PREFIX):
        return "USD"
    if asset_id.startswith(_FX_PREFIX):
        return asset_id.split("/", 1)[-1].upper() if "/" in asset_id else "USD"
    return "USDT"


async def _price_in_eur(asset_id: str) -> Decimal | None:
    live_price = await live.get_live_price(asset_id)
    if not live_price:
        return None
    price = Decimal(str(live_price["price"]))
    currency = _quote_currency(asset_id)
    resolved = await fx_service.get_rate_to_eur(currency, date.today())
    if resolved is None:
        return None
    return price * Decimal(resolved["rate"])


async def get_derived_portfolio(user_id: str) -> dict:
    """Posiciones abiertas derivadas del libro, valoradas en EUR."""
    async with SessionLocal() as session:
        book = await operations_repository.list_book(session, user_id)
    fifo = calculate_fifo(book)

    # Agrega los lotes abiertos por activo (coste medio ponderado en EUR).
    by_asset: dict[str, dict] = {}
    for lot in fifo.open_lots:
        asset_id = lot["assetId"]
        row = by_asset.setdefault(
            asset_id,
            {"assetId": asset_id, "quantity": Decimal("0"), "costEur": Decimal("0")},
        )
        row["quantity"] += lot["remainingQuantity"]
        row["costEur"] += lot["costEur"]

    positions: list[dict] = []
    total_cost = Decimal("0")
    total_value = Decimal("0")
    valued_cost = Decimal("0")
    for asset_id in sorted(by_asset):
        row = by_asset[asset_id]
        quantity = row["quantity"]
        cost_eur = row["costEur"]
        total_cost += cost_eur
        price_eur = await _price_in_eur(asset_id)
        market_value = price_eur * quantity if price_eur is not None else None
        pnl = market_value - cost_eur if market_value is not None else None
        pnl_percent = (
            (pnl / cost_eur * Decimal("100"))
            if (pnl is not None and cost_eur != 0)
            else None
        )
        if market_value is not None:
            total_value += market_value
            valued_cost += cost_eur
        positions.append(
            {
                "assetId": asset_id,
                "quantity": _fixed(quantity),
                "avgCostEur": _money(cost_eur / quantity) if quantity != 0 else "0.00",
                "costEur": _money(cost_eur),
                "priceEur": _money(price_eur) if price_eur is not None else None,
                "marketValueEur": _money(market_value) if market_value is not None else None,
                "pnlEur": _money(pnl) if pnl is not None else None,
                "pnlPercent": _fixed(pnl_percent) if pnl_percent is not None else None,
            }
        )

    total_pnl = total_value - valued_cost
    total_pnl_percent = (
        _fixed(total_pnl / valued_cost * Decimal("100")) if valued_cost != 0 else None
    )
    return {
        "positions": positions,
        "summary": {
            "totalCostEur": _money(total_cost),
            "totalValueEur": _money(total_value),
            "totalPnlEur": _money(total_pnl),
            "totalPnlPercent": total_pnl_percent,
            "positions": len(positions),
        },
        "note": (
            "Cartera derivada del libro de operaciones (FIFO). El valor de "
            "mercado es orientativo; usa precio en vivo y cambio del BCE."
        ),
    }



