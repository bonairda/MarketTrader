"""Importación y exportación del libro de operaciones (CSV/JSON).

El export reutiliza la serialización canónica. El import valida cada fila,
toma SIEMPRE el user_id del usuario autenticado (nunca del payload), deduplica
por (source, external_id) y admite dry-run para previsualizar sin escribir.
"""

from __future__ import annotations

import csv
import io
import json

from app.core.errors import AppError
from app.modules.operations import repository, service

# Cabeceras del CSV de exportación (una fila por operación).
_EXPORT_FIELDS = [
    "id",
    "assetId",
    "side",
    "tradeDate",
    "executedAt",
    "quantity",
    "unitPriceOriginal",
    "grossAmountOriginal",
    "feesOriginal",
    "currency",
    "fxRateToEur",
    "grossAmountEur",
    "feesEur",
    "cashAmountEur",
    "fxSource",
    "source",
    "externalId",
    "notes",
    "createdAt",
]

# Campos aceptados al importar (el resto se ignora).
_IMPORT_STRING_FIELDS = {
    "assetId": "asset_id",
    "side": "side",
    "tradeDate": "trade_date",
    "executedAt": "executed_at",
    "quantity": "quantity",
    "unitPriceOriginal": "unit_price_original",
    "grossAmountOriginal": "gross_amount_original",
    "feesOriginal": "fees_original",
    "currency": "currency",
    "fxRateToEur": "fx_rate_to_eur",
    "fxSource": "fx_source",
    "externalId": "external_id",
    "notes": "notes",
}


async def export_operations(user_id: str) -> list[dict]:
    return await service.list_operations(user_id, limit=100000, offset=0)


def export_json(operations: list[dict]) -> str:
    return json.dumps({"operations": operations}, ensure_ascii=False, indent=2)


def export_csv(operations: list[dict]) -> str:
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(
        output, fieldnames=_EXPORT_FIELDS, delimiter=";", lineterminator="\n"
    )
    writer.writeheader()
    for op in operations:
        writer.writerow({field: op.get(field, "") for field in _EXPORT_FIELDS})
    return output.getvalue()


def _row_to_service_dict(row: dict) -> dict:
    result: dict = {"source": "IMPORT"}
    for source_key, target_key in _IMPORT_STRING_FIELDS.items():
        if source_key in row and row[source_key] not in (None, ""):
            result[target_key] = row[source_key]
    return result


def parse_import_payload(content: str, content_type: str) -> list[dict]:
    """Convierte CSV o JSON en filas normalizadas para el servicio."""
    if content_type == "json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AppError(
                "JSON no válido", code="INVALID_IMPORT", status_code=422
            ) from exc
        rows = data.get("operations") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise AppError(
                "El JSON debe contener una lista 'operations'",
                code="INVALID_IMPORT",
                status_code=422,
            )
        return [_row_to_service_dict(row) for row in rows if isinstance(row, dict)]

    # CSV: acepta separador ';' (export propio) o ','.
    sample = content[:2048]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")), delimiter=delimiter)
    return [_row_to_service_dict(row) for row in reader]


async def import_operations(
    user_id: str, rows: list[dict], *, dry_run: bool = False
) -> dict:
    """Importa filas de forma idempotente. Devuelve un resumen por fila.

    - Sin externalId no hay dedupe posible: se marca como error para no crear
      duplicados silenciosos en reimportaciones.
    - dry_run valida y detecta duplicados sin escribir nada.
    """
    if not rows:
        raise AppError("No hay operaciones que importar", code="EMPTY_IMPORT", status_code=422)

    existing = {
        op["externalId"]
        for op in await service.list_operations(user_id, limit=100000, offset=0)
        if op.get("externalId")
    }

    created = 0
    skipped = 0
    errors: list[dict] = []
    seen_in_batch: set[str] = set()

    for index, row in enumerate(rows):
        external_id = (row.get("external_id") or "").strip()
        if not external_id:
            errors.append({"row": index + 1, "error": "MISSING_EXTERNAL_ID"})
            continue
        if external_id in existing or external_id in seen_in_batch:
            skipped += 1
            continue
        try:
            if dry_run:
                # Valida forma y FX sin persistir.
                prepared = await service.prepare_import_row(row)
                service.validate_prepared(prepared)
            else:
                await service.create_operation(user_id, row)
            seen_in_batch.add(external_id)
            created += 1
        except AppError as exc:
            if exc.code == "DUPLICATE_EXTERNAL_OPERATION":
                skipped += 1
            else:
                errors.append({"row": index + 1, "error": exc.code, "message": exc.message})

    return {
        "dryRun": dry_run,
        "received": len(rows),
        "created": created,
        "skipped": skipped,
        "failed": len(errors),
        "errors": errors[:50],
    }
