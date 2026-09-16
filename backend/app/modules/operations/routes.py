"""Endpoints del libro de operaciones y del informe fiscal FIFO."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field, field_validator

from app.core.errors import AppError
from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.operations import brokers, service
from app.modules.operations import io as operations_io
from app.providers.symbols import normalize_asset_id

router = APIRouter(tags=["operations", "tax"])


class OperationIn(BaseModel):
    assetId: str = Field(min_length=1, max_length=120)
    side: str
    tradeDate: date
    executedAt: datetime | None = None
    quantity: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    unitPriceOriginal: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    grossAmountOriginal: Decimal = Field(gt=0, max_digits=30, decimal_places=12)
    feesOriginal: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=30, decimal_places=12
    )
    currency: str = Field(min_length=3, max_length=12)
    # Opcional: si falta y fxSource=ECB, se resuelve automáticamente por fecha.
    fxRateToEur: Decimal | None = Field(
        default=None, gt=0, max_digits=24, decimal_places=12
    )
    fxSource: str | None = Field(default="USER", max_length=80)
    source: str = Field(default="MANUAL", max_length=80)
    externalId: str | None = Field(default=None, max_length=250)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("side", "currency", "source", "fxSource")
    @classmethod
    def uppercase(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    def to_service_dict(self) -> dict:
        return {
            "asset_id": self.assetId,
            "side": self.side,
            "trade_date": self.tradeDate,
            "executed_at": self.executedAt,
            "quantity": self.quantity,
            "unit_price_original": self.unitPriceOriginal,
            "gross_amount_original": self.grossAmountOriginal,
            "fees_original": self.feesOriginal,
            "currency": self.currency,
            "fx_rate_to_eur": self.fxRateToEur,
            "fx_source": self.fxSource,
            "source": self.source,
            "external_id": self.externalId,
            "notes": self.notes,
        }


@router.get("/operations")
async def list_operations(
    asset_id: str | None = Query(default=None, alias="assetId"),
    side: str | None = Query(default=None, pattern="^(BUY|SELL)$"),
    year: int | None = Query(default=None, ge=1900),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return await service.list_operations_page(
        user.id,
        asset_id=normalize_asset_id(asset_id) if asset_id else None,
        side=side,
        year=year,
        limit=limit,
        offset=offset,
    )


@router.post("/operations", status_code=201)
async def create_operation(
    body: OperationIn, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return await service.create_operation(user.id, body.to_service_dict())


class ImportIn(BaseModel):
    format: str = Field(default="json", pattern="^(json|csv)$")
    content: str = Field(min_length=1)
    dryRun: bool = False


@router.get("/operations/export")
async def export_operations(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    operations = await operations_io.export_operations(user.id)
    if format == "csv":
        content = operations_io.export_csv(operations)
        media_type = "text/csv; charset=utf-8"
        filename = "markettracker-operaciones.csv"
    else:
        content = operations_io.export_json(operations)
        media_type = "application/json; charset=utf-8"
        filename = "markettracker-operaciones.json"
    return Response(
        content=content.encode("utf-8"),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/operations/import")
async def import_operations(
    body: ImportIn, user: CurrentUser = Depends(get_current_user)
) -> dict:
    rows = operations_io.parse_import_payload(body.content, body.format)
    if len(rows) > 5000:
        raise AppError(
            "Máximo 5000 operaciones por importación",
            code="IMPORT_TOO_LARGE",
            status_code=422,
        )
    return await operations_io.import_operations(user.id, rows, dry_run=body.dryRun)


class BrokerImportIn(BaseModel):
    broker: str = Field(pattern="^(generic|trade_republic|revolut)$")
    content: str = Field(min_length=1)
    dryRun: bool = True


@router.get("/operations/brokers")
async def supported_brokers(
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return {"brokers": list(brokers.SUPPORTED_BROKERS)}


@router.post("/operations/import/broker")
async def import_broker_csv(
    body: BrokerImportIn, user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Importa el CSV de un broker soportado. Por defecto en modo previsualización."""
    mapped = brokers.map_broker_csv(body.broker, body.content)
    if len(mapped) > 5000:
        raise AppError(
            "Máximo 5000 operaciones por importación",
            code="IMPORT_TOO_LARGE",
            status_code=422,
        )
    rows = operations_io.rows_to_service_dicts(mapped)
    return await operations_io.import_operations(user.id, rows, dry_run=body.dryRun)


@router.get("/operations/audit")
async def operation_audit_log(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await service.list_audit_log(user.id, limit=limit, offset=offset)


@router.get("/operations/{operation_id}")
async def get_operation(
    operation_id: str, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return await service.get_operation(user.id, operation_id)


@router.delete("/operations/{operation_id}", status_code=204)
async def delete_operation(
    operation_id: str, user: CurrentUser = Depends(get_current_user)
) -> None:
    await service.delete_operation(user.id, operation_id)


@router.get("/tax/reports/{year}")
async def tax_report(
    year: int, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return await service.get_tax_report(user.id, year)


@router.get("/tax/reports/{year}/csv")
async def tax_report_csv(
    year: int, user: CurrentUser = Depends(get_current_user)
) -> Response:
    report = await service.get_tax_report(user.id, year)
    content = service.tax_report_csv(report)
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="markettracker-fiscal-{year}.csv"'
            )
        },
    )
