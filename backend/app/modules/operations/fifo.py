"""Motor FIFO fiscal puro, sin acceso a base de datos.

Todos los cálculos usan Decimal. No se redondea durante el emparejamiento;
la cuantización se realiza únicamente al serializar la respuesta o el CSV.
La dirección del cambio es siempre: 1 unidad de divisa original = N EUR.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Iterable

ZERO = Decimal("0")


class InsufficientHoldingsError(ValueError):
    """Una venta supera las compras anteriores disponibles para el activo."""

    def __init__(self, asset_id: str, required: Decimal, available: Decimal):
        self.asset_id = asset_id
        self.required = required
        self.available = available
        super().__init__(
            f"Venta de {required} {asset_id} con solo {available} disponible"
        )


@dataclass
class _Lot:
    operation_id: str
    asset_id: str
    acquisition_date: date
    currency: str
    fx_rate_to_eur: Decimal
    remaining: Decimal
    gross_unit_original: Decimal
    fee_unit_original: Decimal
    gross_unit_eur: Decimal
    fee_unit_eur: Decimal


@dataclass(frozen=True)
class FifoResult:
    disposals: list[dict]
    open_lots: list[dict]


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _datetime(value: object | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _operation_sort_key(operation: dict) -> tuple:
    """Orden fiscal determinista; sin hora, la operación queda al final del día."""
    trade_date = _date(operation["tradeDate"])
    executed = _datetime(operation.get("executedAt"))
    created = _datetime(operation.get("createdAt"))
    end_of_day = datetime.max.replace(tzinfo=UTC)
    return (
        trade_date,
        executed is None,
        executed or end_of_day,
        created or end_of_day,
        str(operation["id"]),
    )


def calculate_fifo(operations: Iterable[dict]) -> FifoResult:
    """Empareja ventas contra los lotes de compra más antiguos por activo.

    La entrada puede mezclar activos. Debe contener las claves camelCase que
    devuelve el repositorio. Si alguna venta excede el inventario anterior,
    lanza InsufficientHoldingsError y no devuelve un resultado parcial.
    """
    lots_by_asset: dict[str, deque[_Lot]] = defaultdict(deque)
    disposals: list[dict] = []

    for operation in sorted(operations, key=_operation_sort_key):
        asset_id = str(operation["assetId"])
        side = str(operation["side"]).upper()
        quantity = _decimal(operation["quantity"])
        gross_original = _decimal(operation["grossAmountOriginal"])
        fees_original = _decimal(operation.get("feesOriginal", ZERO))
        fx = _decimal(operation["fxRateToEur"])
        gross_eur = gross_original * fx
        fees_eur = fees_original * fx
        operation_date = _date(operation["tradeDate"])

        if side == "BUY":
            lots_by_asset[asset_id].append(
                _Lot(
                    operation_id=str(operation["id"]),
                    asset_id=asset_id,
                    acquisition_date=operation_date,
                    currency=str(operation["currency"]),
                    fx_rate_to_eur=fx,
                    remaining=quantity,
                    gross_unit_original=gross_original / quantity,
                    fee_unit_original=fees_original / quantity,
                    gross_unit_eur=gross_eur / quantity,
                    fee_unit_eur=fees_eur / quantity,
                )
            )
            continue
        if side != "SELL":
            raise ValueError(f"Tipo de operación no soportado: {side}")

        available = sum((lot.remaining for lot in lots_by_asset[asset_id]), ZERO)
        if available < quantity:
            raise InsufficientHoldingsError(asset_id, quantity, available)

        remaining_to_sell = quantity
        sale_gross_unit_eur = gross_eur / quantity
        sale_fee_unit_eur = fees_eur / quantity
        while remaining_to_sell > ZERO:
            lot = lots_by_asset[asset_id][0]
            matched = min(remaining_to_sell, lot.remaining)
            acquisition_gross_original = lot.gross_unit_original * matched
            acquisition_fees_original = lot.fee_unit_original * matched
            acquisition_gross = lot.gross_unit_eur * matched
            acquisition_fees = lot.fee_unit_eur * matched
            acquisition_cost = acquisition_gross + acquisition_fees
            sale_gross_original = (gross_original / quantity) * matched
            sale_fees_original = (fees_original / quantity) * matched
            sale_gross = sale_gross_unit_eur * matched
            sale_fees = sale_fee_unit_eur * matched
            proceeds = sale_gross - sale_fees
            disposals.append(
                {
                    "assetId": asset_id,
                    "sellOperationId": str(operation["id"]),
                    "saleDate": operation_date,
                    "saleCurrency": str(operation["currency"]),
                    "saleFxRateToEur": fx,
                    "saleGrossOriginal": sale_gross_original,
                    "saleFeesOriginal": sale_fees_original,
                    "buyOperationId": lot.operation_id,
                    "acquisitionDate": lot.acquisition_date,
                    "acquisitionCurrency": lot.currency,
                    "acquisitionFxRateToEur": lot.fx_rate_to_eur,
                    "acquisitionGrossOriginal": acquisition_gross_original,
                    "acquisitionFeesOriginal": acquisition_fees_original,
                    "matchedQuantity": matched,
                    "saleGrossEur": sale_gross,
                    "saleFeesEur": sale_fees,
                    "proceedsEur": proceeds,
                    "acquisitionGrossEur": acquisition_gross,
                    "acquisitionFeesEur": acquisition_fees,
                    "acquisitionCostEur": acquisition_cost,
                    "gainEur": proceeds - acquisition_cost,
                }
            )
            lot.remaining -= matched
            remaining_to_sell -= matched
            if lot.remaining == ZERO:
                lots_by_asset[asset_id].popleft()

    open_lots = [
        {
            "assetId": asset_id,
            "buyOperationId": lot.operation_id,
            "acquisitionDate": lot.acquisition_date,
            "remainingQuantity": lot.remaining,
            "unitCostEur": lot.gross_unit_eur + lot.fee_unit_eur,
            "costEur": lot.remaining * (lot.gross_unit_eur + lot.fee_unit_eur),
            "currency": lot.currency,
        }
        for asset_id, lots in sorted(lots_by_asset.items())
        for lot in lots
        if lot.remaining > ZERO
    ]
    return FifoResult(disposals=disposals, open_lots=open_lots)


def _buy_dates_by_asset(operations: Iterable[dict]) -> dict[str, list[date]]:
    buys: dict[str, list[date]] = defaultdict(list)
    for op in operations:
        if str(op["side"]).upper() == "BUY":
            buys[str(op["assetId"])].append(_date(op["tradeDate"]))
    return buys


def _annotate_wash_sales(
    disposals: list[dict],
    buys_by_asset: dict[str, list[date]],
    *,
    window_days: int = 60,
) -> None:
    """Marca pérdidas potencialmente no deducibles por recompra homogénea (AEAT).

    Regla orientativa: una pérdida no es computable si se adquieren valores
    homogéneos del mismo activo dentro de una ventana alrededor de la venta
    (±2 meses para valores cotizados). Se marca `washSale` y se explica; NO se
    modifica la ganancia/pérdida, solo se informa.
    """
    window = timedelta(days=window_days)
    for disposal in disposals:
        disposal["washSale"] = False
        disposal["washSaleReason"] = None
        if disposal["gainEur"] >= ZERO:
            continue
        sale_date = disposal["saleDate"]
        repurchase = any(
            abs((buy_date - sale_date).days) <= window.days
            and buy_date != disposal["acquisitionDate"]
            for buy_date in buys_by_asset.get(disposal["assetId"], [])
        )
        if repurchase:
            disposal["washSale"] = True
            disposal["washSaleReason"] = (
                "Posible recompra de valores homogéneos en ±2 meses: la pérdida "
                "podría no ser computable este ejercicio (revisar con asesor)."
            )


def build_tax_report(operations: Iterable[dict], year: int) -> dict:
    """Construye un informe anual usando todo el historial hasta fin de `year`."""
    operations = list(operations)
    relevant = [op for op in operations if _date(op["tradeDate"]).year <= year]
    fifo = calculate_fifo(relevant)
    disposals = [d for d in fifo.disposals if d["saleDate"].year == year]
    # La recompra puede ocurrir en el ejercicio siguiente, así que se evalúa
    # contra TODAS las compras del historial, no solo hasta fin de año.
    _annotate_wash_sales(disposals, _buy_dates_by_asset(operations))

    by_asset: dict[str, dict] = {}
    for disposal in disposals:
        asset_id = disposal["assetId"]
        row = by_asset.setdefault(
            asset_id,
            {
                "assetId": asset_id,
                "quantitySold": ZERO,
                "proceedsEur": ZERO,
                "acquisitionCostEur": ZERO,
                "feesEur": ZERO,
                "realizedGainEur": ZERO,
            },
        )
        row["quantitySold"] += disposal["matchedQuantity"]
        row["proceedsEur"] += disposal["proceedsEur"]
        row["acquisitionCostEur"] += disposal["acquisitionCostEur"]
        row["feesEur"] += disposal["saleFeesEur"] + disposal["acquisitionFeesEur"]
        row["realizedGainEur"] += disposal["gainEur"]

    assets = [by_asset[key] for key in sorted(by_asset)]
    summary = {
        "sellOperations": len({d["sellOperationId"] for d in disposals}),
        "matchedLots": len(disposals),
        "proceedsEur": sum((d["proceedsEur"] for d in disposals), ZERO),
        "acquisitionCostEur": sum(
            (d["acquisitionCostEur"] for d in disposals), ZERO
        ),
        "feesEur": sum(
            (d["saleFeesEur"] + d["acquisitionFeesEur"] for d in disposals),
            ZERO,
        ),
        "realizedGainEur": sum((d["gainEur"] for d in disposals), ZERO),
        "washSaleDisposals": sum(1 for d in disposals if d.get("washSale")),
        "washSaleAdjustmentEur": sum(
            (-d["gainEur"] for d in disposals if d.get("washSale")), ZERO
        ),
    }
    return {
        "year": year,
        "currency": "EUR",
        "summary": summary,
        "assets": assets,
        "disposals": disposals,
        "openLots": fifo.open_lots,
    }
