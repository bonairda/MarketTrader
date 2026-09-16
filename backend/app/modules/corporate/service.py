"""Servicio de eventos corporativos: validación, FX y resumen fiscal."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, NotFoundError
from app.modules.corporate import repository
from app.modules.fx import service as fx_service
from app.providers.symbols import normalize_asset_id

_MONEY = Decimal("0.01")


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value: object) -> str:
    return format(_decimal(value).quantize(_MONEY, rounding=ROUND_HALF_UP), "f")


def _iso(value: object | None) -> str | None:
    return value.isoformat() if isinstance(value, date | datetime) else value


async def _resolve_fx(currency: str, on: date, provided: Decimal | None) -> tuple[Decimal, str]:
    if provided is not None:
        return provided, "USER"
    if currency.upper() == "EUR":
        return Decimal("1"), "ECB"
    resolved = await fx_service.get_rate_to_eur(currency, on)
    if resolved is None:
        raise AppError(
            "No se pudo obtener el tipo de cambio; indícalo manualmente",
            code="FX_UNAVAILABLE",
            status_code=422,
        )
    return Decimal(resolved["rate"]), resolved["source"]


def serialize_event(event: dict) -> dict:
    fx = event.get("fxRateToEur")
    gross = event.get("grossAmountOriginal")
    withholding = event.get("withholdingOriginal")
    result = {
        "id": event["id"],
        "assetId": event["assetId"],
        "type": event["type"],
        "eventDate": _iso(event["eventDate"]),
        "currency": event.get("currency"),
        "fxRateToEur": format(_decimal(fx), "f") if fx is not None else None,
        "ratio": format(_decimal(event["ratio"]), "f") if event.get("ratio") is not None else None,
        "fxSource": event.get("fxSource"),
        "externalId": event.get("externalId"),
        "notes": event.get("notes"),
        "createdAt": _iso(event.get("createdAt")),
    }
    if gross is not None:
        result["grossAmountOriginal"] = format(_decimal(gross), "f")
        result["grossAmountEur"] = _money(_decimal(gross) * _decimal(fx))
    if withholding is not None:
        result["withholdingOriginal"] = format(_decimal(withholding), "f")
        result["withholdingEur"] = _money(_decimal(withholding) * _decimal(fx))
    if gross is not None and withholding is not None:
        net = (_decimal(gross) - _decimal(withholding)) * _decimal(fx)
        result["netAmountEur"] = _money(net)
    return result


async def list_events(user_id: str, **filters) -> list[dict]:
    rows = await repository.list_events(user_id, **filters)
    return [serialize_event(r) for r in rows]


async def add_event(user_id: str, data: dict) -> dict:
    event_type = str(data["type"]).upper()
    if event_type not in {"DIVIDEND", "SPLIT"}:
        raise AppError("Tipo de evento no válido", code="INVALID_EVENT_TYPE", status_code=422)
    asset_id = normalize_asset_id(str(data["asset_id"]))
    event_date = data["event_date"]
    if not isinstance(event_date, date):
        event_date = date.fromisoformat(str(event_date))
    if event_date > date.today():
        raise AppError("La fecha no puede estar en el futuro", code="FUTURE_EVENT", status_code=422)

    record = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "asset_id": asset_id,
        "type": event_type,
        "event_date": event_date,
        "gross_amount_original": None,
        "withholding_original": None,
        "currency": None,
        "fx_rate_to_eur": None,
        "ratio": None,
        "fx_source": None,
        "external_id": (data.get("external_id") or "").strip() or None,
        "notes": (data.get("notes") or "").strip() or None,
    }

    if event_type == "DIVIDEND":
        gross = _decimal(data["gross_amount_original"])
        withholding = _decimal(data.get("withholding_original", 0))
        if gross <= 0 or withholding < 0 or withholding > gross:
            raise AppError(
                "Importe/retención de dividendo no válidos",
                code="INVALID_DIVIDEND",
                status_code=422,
            )
        currency = str(data["currency"]).upper()
        fx, fx_source = await _resolve_fx(currency, event_date, data.get("fx_rate_to_eur"))
        record.update(
            gross_amount_original=gross,
            withholding_original=withholding,
            currency=currency,
            fx_rate_to_eur=fx,
            fx_source=fx_source,
        )
    else:  # SPLIT
        ratio = _decimal(data["ratio"])
        if ratio <= 0:
            raise AppError("El ratio del split debe ser positivo", code="INVALID_SPLIT", status_code=422)
        record["ratio"] = ratio

    try:
        await repository.insert_event(record)
    except IntegrityError as exc:
        raise AppError(
            "El evento ya fue importado", code="DUPLICATE_EVENT", status_code=409
        ) from exc
    events = await repository.list_events(user_id, limit=1, offset=0)
    for event in events:
        if event["id"] == record["id"]:
            return serialize_event(event)
    # Fallback: serializa desde el record (mismas claves camelCase).
    return serialize_event(
        {
            "id": record["id"],
            "assetId": asset_id,
            "type": event_type,
            "eventDate": event_date,
            "grossAmountOriginal": record["gross_amount_original"],
            "withholdingOriginal": record["withholding_original"],
            "currency": record["currency"],
            "fxRateToEur": record["fx_rate_to_eur"],
            "ratio": record["ratio"],
            "fxSource": record["fx_source"],
            "externalId": record["external_id"],
            "notes": record["notes"],
            "createdAt": None,
        }
    )


async def delete_event(user_id: str, event_id: str) -> None:
    affected = await repository.delete_event(user_id, event_id)
    if affected == 0:
        raise NotFoundError("Evento no encontrado")


async def dividend_summary(user_id: str, year: int) -> dict:
    """Resumen de dividendos del ejercicio, en EUR, para la declaración."""
    dividends = await repository.list_dividends_for_year(user_id, year)
    gross_eur = Decimal("0")
    withholding_eur = Decimal("0")
    for div in dividends:
        fx = _decimal(div["fxRateToEur"])
        gross_eur += _decimal(div["grossAmountOriginal"]) * fx
        withholding_eur += _decimal(div["withholdingOriginal"] or 0) * fx
    return {
        "year": year,
        "count": len(dividends),
        "grossEur": _money(gross_eur),
        "withholdingEur": _money(withholding_eur),
        "netEur": _money(gross_eur - withholding_eur),
    }
