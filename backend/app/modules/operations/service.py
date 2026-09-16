"""Servicio transaccional de operaciones e informes fiscales."""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from sqlalchemy.exc import IntegrityError

from app.core.db import SessionLocal
from app.core.errors import AppError, NotFoundError
from app.modules.corporate import service as corporate_service
from app.modules.fx import service as fx_service
from app.modules.operations import repository
from app.modules.operations.fifo import (
    InsufficientHoldingsError,
    build_tax_report,
    calculate_fifo,
)
from app.providers.symbols import normalize_asset_id

_MONEY = Decimal("0.01")
_QUANTITY = Decimal("0.000000000001")
_CURRENCY_RE = re.compile(r"^[A-Z0-9]{3,12}$")


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _require_db_precision(
    value: Decimal, *, max_digits: int = 30, decimal_places: int = 12
) -> Decimal:
    """Rechaza valores que PostgreSQL tendría que redondear o desbordar."""
    quantum = Decimal(1).scaleb(-decimal_places)
    if not value.is_finite():
        raise AppError(
            "El valor debe ser un decimal finito",
            code="INVALID_PRECISION",
            status_code=422,
        )
    try:
        normalized = value.quantize(quantum)
    except InvalidOperation as exc:
        raise AppError(
            "El valor excede la precisión admitida",
            code="INVALID_PRECISION",
            status_code=422,
        ) from exc
    integer_digits = max(0, normalized.adjusted() + 1) if normalized else 0
    if normalized != value or integer_digits > max_digits - decimal_places:
        raise AppError(
            f"Máximo {max_digits - decimal_places} enteros y {decimal_places} decimales",
            code="INVALID_PRECISION",
            status_code=422,
        )
    return normalized


def _fixed(value: object, quantum: Decimal = _QUANTITY) -> str:
    return format(_decimal(value).quantize(quantum, rounding=ROUND_HALF_UP), "f")


def _money(value: object) -> str:
    return _fixed(value, _MONEY)


def _iso(value: object | None) -> str | None:
    return value.isoformat() if isinstance(value, date | datetime) else value


def _validate_input(data: dict) -> dict:
    asset_id = normalize_asset_id(str(data["asset_id"]))
    side = str(data["side"]).upper()
    if side not in {"BUY", "SELL"}:
        raise AppError("El tipo debe ser BUY o SELL", code="INVALID_SIDE", status_code=422)

    quantity = _require_db_precision(_decimal(data["quantity"]))
    unit_price = _require_db_precision(_decimal(data["unit_price_original"]))
    gross = _require_db_precision(_decimal(data["gross_amount_original"]))
    fees = _require_db_precision(_decimal(data.get("fees_original", 0)))
    fx = _require_db_precision(
        _decimal(data["fx_rate_to_eur"]), max_digits=24, decimal_places=12
    )
    if quantity <= 0 or unit_price <= 0 or gross <= 0 or fx <= 0 or fees < 0:
        raise AppError(
            "Cantidad, precio, bruto y cambio deben ser positivos; comisión no negativa",
            code="INVALID_AMOUNTS",
            status_code=422,
        )
    if fees > gross:
        raise AppError(
            "La comisión no puede superar el importe bruto",
            code="INVALID_FEES",
            status_code=422,
        )

    expected_gross = quantity * unit_price
    tolerance = max(Decimal("0.01"), expected_gross * Decimal("0.001"))
    if abs(gross - expected_gross) > tolerance:
        raise AppError(
            "El importe bruto no concuerda con cantidad × precio",
            code="GROSS_MISMATCH",
            status_code=422,
        )

    trade_date = data["trade_date"]
    if trade_date > date.today():
        raise AppError(
            "La fecha de operación no puede estar en el futuro",
            code="FUTURE_OPERATION",
            status_code=422,
        )
    currency = str(data["currency"]).upper().strip()
    if not _CURRENCY_RE.fullmatch(currency):
        raise AppError(
            "Código de divisa no válido", code="INVALID_CURRENCY", status_code=422
        )

    return {
        "asset_id": asset_id,
        "side": side,
        "trade_date": trade_date,
        "executed_at": data.get("executed_at"),
        "quantity": quantity,
        "unit_price_original": unit_price,
        "gross_amount_original": gross,
        "fees_original": fees,
        "currency": currency,
        "fx_rate_to_eur": fx,
        "fx_source": (data.get("fx_source") or "USER").strip().upper(),
        "source": (data.get("source") or "MANUAL").strip().upper(),
        "external_id": (data.get("external_id") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
    }


def _candidate_for_fifo(operation: dict) -> dict:
    return {
        "id": operation["id"],
        "assetId": operation["asset_id"],
        "side": operation["side"],
        "tradeDate": operation["trade_date"],
        "executedAt": operation["executed_at"],
        "quantity": operation["quantity"],
        "grossAmountOriginal": operation["gross_amount_original"],
        "feesOriginal": operation["fees_original"],
        "currency": operation["currency"],
        "fxRateToEur": operation["fx_rate_to_eur"],
        # El candidato es posterior a operaciones existentes sin hora del mismo día.
        "createdAt": datetime.max.replace(tzinfo=UTC),
    }


def serialize_operation(operation: dict) -> dict:
    gross_eur = _decimal(operation["grossAmountOriginal"]) * _decimal(
        operation["fxRateToEur"]
    )
    fees_eur = _decimal(operation["feesOriginal"]) * _decimal(
        operation["fxRateToEur"]
    )
    cash_eur = gross_eur + fees_eur if operation["side"] == "BUY" else gross_eur - fees_eur
    return {
        "id": operation["id"],
        "assetId": operation["assetId"],
        "side": operation["side"],
        "tradeDate": _iso(operation["tradeDate"]),
        "executedAt": _iso(operation.get("executedAt")),
        "quantity": _fixed(operation["quantity"]),
        "unitPriceOriginal": _fixed(operation["unitPriceOriginal"]),
        "grossAmountOriginal": _fixed(operation["grossAmountOriginal"]),
        "feesOriginal": _fixed(operation["feesOriginal"]),
        "currency": operation["currency"],
        "fxRateToEur": _fixed(operation["fxRateToEur"]),
        "grossAmountEur": _money(gross_eur),
        "feesEur": _money(fees_eur),
        "cashAmountEur": _money(cash_eur),
        "fxSource": operation.get("fxSource"),
        "source": operation["source"],
        "externalId": operation.get("externalId"),
        "notes": operation.get("notes"),
        "createdAt": _iso(operation.get("createdAt")),
    }


async def list_operations(user_id: str, **filters) -> list[dict]:
    rows = await repository.list_operations(user_id, **filters)
    return [serialize_operation(row) for row in rows]


async def list_operations_page(
    user_id: str,
    *,
    asset_id: str | None = None,
    side: str | None = None,
    year: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Página de operaciones con metadatos para scroll incremental."""
    items = await list_operations(
        user_id,
        asset_id=asset_id,
        side=side,
        year=year,
        limit=limit,
        offset=offset,
    )
    total = await repository.count_operations(
        user_id, asset_id=asset_id, side=side, year=year
    )
    next_offset = offset + len(items)
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasMore": next_offset < total,
        "nextOffset": next_offset if next_offset < total else None,
    }


async def get_operation(user_id: str, operation_id: str) -> dict:
    operation = await repository.get_operation(user_id, operation_id)
    if not operation:
        raise NotFoundError("Operación no encontrada")
    return serialize_operation(operation)


def _integrity_constraint(exc: IntegrityError) -> str | None:
    origin = exc.orig
    return getattr(origin, "constraint_name", None) or getattr(
        getattr(origin, "__cause__", None), "constraint_name", None
    )


async def _resolve_fx_if_missing(data: dict) -> dict:
    """Autorrellena fx_rate_to_eur desde el BCE cuando no se ha proporcionado.

    Solo actúa si falta la tasa. La fuente declarada pasa a reflejar el origen
    real (ECB o su aproximación). Si el BCE no resuelve, se exige tasa manual.
    """
    if data.get("fx_rate_to_eur") is not None:
        return data
    trade_date = data["trade_date"]
    if not isinstance(trade_date, date):
        trade_date = date.fromisoformat(str(trade_date))
    resolved = await fx_service.get_rate_to_eur(str(data["currency"]), trade_date)
    if resolved is None:
        raise AppError(
            "No se pudo obtener el tipo de cambio; indícalo manualmente",
            code="FX_UNAVAILABLE",
            status_code=422,
        )
    enriched = dict(data)
    enriched["fx_rate_to_eur"] = Decimal(resolved["rate"])
    enriched["fx_source"] = resolved["source"]
    return enriched


async def prepare_import_row(data: dict) -> dict:
    """Resuelve el FX de una fila de importación (para dry-run)."""
    return await _resolve_fx_if_missing(data)


def validate_prepared(data: dict) -> dict:
    """Valida la forma/importes de una fila ya con FX resuelto (dry-run)."""
    return _validate_input(data)


async def create_operation(user_id: str, data: dict) -> dict:
    data = await _resolve_fx_if_missing(data)
    values = _validate_input(data)
    values.update({"id": str(uuid.uuid4()), "user_id": user_id})
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await repository.acquire_book_lock(session, user_id, values["asset_id"])
                current = await repository.list_book(
                    session, user_id, asset_id=values["asset_id"]
                )
                try:
                    calculate_fifo([*current, _candidate_for_fifo(values)])
                except InsufficientHoldingsError as exc:
                    raise AppError(
                        str(exc), code="INSUFFICIENT_HOLDINGS", status_code=409
                    ) from exc
                await repository.insert_operation(session, values)
                persisted = await repository.get_operation_for_update(
                    session, user_id, values["id"]
                )
                if not persisted:
                    raise RuntimeError("La operación insertada no se pudo releer")
                await repository.insert_audit_log(
                    session,
                    user_id=user_id,
                    operation_id=values["id"],
                    action="CREATE",
                    payload=serialize_operation(persisted),
                )
    except IntegrityError as exc:
        if _integrity_constraint(exc) != "ux_operations_user_source_external_id":
            raise
        raise AppError(
            "La operación ya fue importada",
            code="DUPLICATE_EXTERNAL_OPERATION",
            status_code=409,
        ) from exc
    return await get_operation(user_id, values["id"])


async def delete_operation(user_id: str, operation_id: str) -> None:
    async with SessionLocal() as session:
        async with session.begin():
            operation = await repository.get_operation_for_update(
                session, user_id, operation_id
            )
            if not operation:
                raise NotFoundError("Operación no encontrada")
            await repository.acquire_book_lock(session, user_id, operation["assetId"])
            remaining = await repository.list_book(
                session,
                user_id,
                asset_id=operation["assetId"],
                exclude_id=operation_id,
            )
            try:
                calculate_fifo(remaining)
            except InsufficientHoldingsError as exc:
                raise AppError(
                    "No se puede borrar: dejaría una venta posterior sin saldo",
                    code="DELETE_BREAKS_FIFO",
                    status_code=409,
                ) from exc
            await repository.insert_audit_log(
                session,
                user_id=user_id,
                operation_id=operation_id,
                action="DELETE",
                payload=serialize_operation(operation),
            )
            await repository.delete_operation(session, operation_id)


async def list_audit_log(
    user_id: str, *, limit: int = 200, offset: int = 0
) -> list[dict]:
    return await repository.list_audit_log(user_id, limit=limit, offset=offset)


def _serialize_disposal(disposal: dict) -> dict:
    decimal_keys = {
        "matchedQuantity": _fixed,
        "saleFxRateToEur": _fixed,
        "saleGrossOriginal": _fixed,
        "saleFeesOriginal": _fixed,
        "acquisitionFxRateToEur": _fixed,
        "acquisitionGrossOriginal": _fixed,
        "acquisitionFeesOriginal": _fixed,
    }
    money_keys = {
        "saleGrossEur",
        "saleFeesEur",
        "proceedsEur",
        "acquisitionGrossEur",
        "acquisitionFeesEur",
        "acquisitionCostEur",
        "gainEur",
    }
    result = {}
    for key, value in disposal.items():
        if key in decimal_keys:
            result[key] = decimal_keys[key](value)
        elif key in money_keys:
            result[key] = _money(value)
        elif isinstance(value, date | datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    # La ganancia visible debe reconciliar exactamente con transmisión menos
    # adquisición visibles, no con un tercer redondeo independiente.
    result["gainEur"] = _money(
        _decimal(result["proceedsEur"]) - _decimal(result["acquisitionCostEur"])
    )
    return result


def serialize_tax_report(report: dict) -> dict:
    # Primero cuantizamos cada emparejamiento. Activos y resumen se derivan de
    # esas mismas filas visibles/exportables para que siempre reconcilien.
    disposals = [_serialize_disposal(row) for row in report["disposals"]]
    by_asset: dict[str, dict] = {}
    for disposal in disposals:
        asset_id = disposal["assetId"]
        row = by_asset.setdefault(
            asset_id,
            {
                "assetId": asset_id,
                "quantitySold": Decimal("0"),
                "proceedsEur": Decimal("0"),
                "acquisitionCostEur": Decimal("0"),
                "feesEur": Decimal("0"),
                "realizedGainEur": Decimal("0"),
            },
        )
        row["quantitySold"] += _decimal(disposal["matchedQuantity"])
        row["proceedsEur"] += _decimal(disposal["proceedsEur"])
        row["acquisitionCostEur"] += _decimal(disposal["acquisitionCostEur"])
        row["feesEur"] += _decimal(disposal["saleFeesEur"]) + _decimal(
            disposal["acquisitionFeesEur"]
        )
        row["realizedGainEur"] += _decimal(disposal["gainEur"])

    assets = [
        {
            **row,
            "quantitySold": _fixed(row["quantitySold"]),
            "proceedsEur": _money(row["proceedsEur"]),
            "acquisitionCostEur": _money(row["acquisitionCostEur"]),
            "feesEur": _money(row["feesEur"]),
            "realizedGainEur": _money(row["realizedGainEur"]),
        }
        for _, row in sorted(by_asset.items())
    ]
    summary = {
        "sellOperations": len({d["sellOperationId"] for d in disposals}),
        "matchedLots": len(disposals),
        "proceedsEur": _money(
            sum((_decimal(d["proceedsEur"]) for d in disposals), Decimal("0"))
        ),
        "acquisitionCostEur": _money(
            sum(
                (_decimal(d["acquisitionCostEur"]) for d in disposals),
                Decimal("0"),
            )
        ),
        "feesEur": _money(
            sum(
                (
                    _decimal(d["saleFeesEur"])
                    + _decimal(d["acquisitionFeesEur"])
                    for d in disposals
                ),
                Decimal("0"),
            )
        ),
        "realizedGainEur": _money(
            sum((_decimal(d["gainEur"]) for d in disposals), Decimal("0"))
        ),
        "washSaleDisposals": sum(1 for d in disposals if d.get("washSale")),
        "washSaleAdjustmentEur": _money(
            sum(
                (-_decimal(d["gainEur"]) for d in disposals if d.get("washSale")),
                Decimal("0"),
            )
        ),
    }
    open_lots = [
        {
            **row,
            "acquisitionDate": _iso(row["acquisitionDate"]),
            "remainingQuantity": _fixed(row["remainingQuantity"]),
            "unitCostEur": _fixed(row["unitCostEur"]),
            "costEur": _money(row["costEur"]),
        }
        for row in report["openLots"]
    ]
    return {
        "year": report["year"],
        "currency": report["currency"],
        "summary": summary,
        "assets": assets,
        "disposals": disposals,
        "openLots": open_lots,
        "disclaimer": (
            "Borrador informativo basado en FIFO. No sustituye asesoramiento fiscal "
            "ni contempla todas las reglas de la AEAT, como recompra de valores homogéneos."
        ),
    }


async def get_tax_report(user_id: str, year: int) -> dict:
    if year < 1900 or year > date.today().year:
        raise AppError("Ejercicio fiscal no válido", code="INVALID_YEAR", status_code=422)
    async with SessionLocal() as session:
        operations = await repository.list_book(session, user_id, through_year=year)
    try:
        report = serialize_tax_report(build_tax_report(operations, year))
    except InsufficientHoldingsError as exc:
        raise AppError(str(exc), code="INVALID_OPERATION_BOOK", status_code=409) from exc
    # Dividendos del ejercicio (sección aparte de las plusvalías FIFO).
    report["dividends"] = await corporate_service.dividend_summary(user_id, year)
    return report


def tax_report_csv(report: dict) -> str:
    """CSV UTF-8 con BOM y separador ';', una fila por emparejamiento FIFO."""
    output = io.StringIO()
    output.write("\ufeff")
    fields = [
        "ejercicio",
        "activo",
        "id_venta",
        "fecha_transmision",
        "id_compra",
        "fecha_adquisicion",
        "cantidad",
        "divisa_venta",
        "cambio_venta_eur",
        "bruto_venta_original",
        "comision_venta_original",
        "valor_transmision_eur",
        "divisa_compra",
        "cambio_compra_eur",
        "bruto_compra_original",
        "comision_compra_original",
        "valor_adquisicion_eur",
        "ganancia_perdida_eur",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, delimiter=";", lineterminator="\n")
    writer.writeheader()
    for row in report["disposals"]:
        writer.writerow(
            {
                "ejercicio": report["year"],
                "activo": row["assetId"],
                "id_venta": row["sellOperationId"],
                "fecha_transmision": row["saleDate"],
                "id_compra": row["buyOperationId"],
                "fecha_adquisicion": row["acquisitionDate"],
                "cantidad": row["matchedQuantity"],
                "divisa_venta": row["saleCurrency"],
                "cambio_venta_eur": row["saleFxRateToEur"],
                "bruto_venta_original": row["saleGrossOriginal"],
                "comision_venta_original": row["saleFeesOriginal"],
                "valor_transmision_eur": row["proceedsEur"],
                "divisa_compra": row["acquisitionCurrency"],
                "cambio_compra_eur": row["acquisitionFxRateToEur"],
                "bruto_compra_original": row["acquisitionGrossOriginal"],
                "comision_compra_original": row["acquisitionFeesOriginal"],
                "valor_adquisicion_eur": row["acquisitionCostEur"],
                "ganancia_perdida_eur": row["gainEur"],
            }
        )
    return output.getvalue()
