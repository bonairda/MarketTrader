"""Mapeadores de CSV de brokers al formato canónico del importador.

Cada broker exporta columnas distintas. Estos mapeadores son funciones puras
que convierten un CSV concreto en filas camelCase compatibles con
`io.parse_import_payload`/`_row_to_service_dict`, sin tocar red ni BD.

Reglas comunes:
- Se genera un `externalId` estable por fila para que reimportar el mismo
  extracto no duplique operaciones (idempotencia por (source, external_id)).
- Solo se emiten compras/ventas; otras filas (dividendos, comisiones sueltas,
  ingresos) se ignoran aquí y se tratan como eventos corporativos aparte.
- No se calcula el tipo de cambio: si la divisa no es EUR se deja `fxSource=ECB`
  para que el backend lo resuelva por fecha.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re

from app.core.errors import AppError

SUPPORTED_BROKERS = ("generic", "trade_republic", "revolut")


def _read_rows(content: str) -> list[dict]:
    text = content.lstrip("\ufeff")
    sample = text[:2048]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def _get(row: dict, *names: str) -> str:
    """Devuelve el primer valor no vacío entre varias posibles cabeceras."""
    for name in names:
        for key, value in row.items():
            if key and key.strip().lower() == name.lower() and value not in (None, ""):
                return str(value).strip()
    return ""


def _decimalish(raw: str) -> str:
    """Normaliza números de broker (miles/decimales europeos) a punto decimal."""
    cleaned = raw.replace("\u00a0", "").replace(" ", "")
    cleaned = re.sub(r"[€$£]", "", cleaned)
    if "," in cleaned and "." in cleaned:
        # Formato europeo 1.234,56 -> 1234.56
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    return cleaned.lstrip("+")


def _stable_external_id(broker: str, parts: list[str]) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{broker}:{digest}"


def _normalize_side(raw: str) -> str | None:
    value = raw.strip().lower()
    if value in {"buy", "compra", "kauf", "purchase"}:
        return "BUY"
    if value in {"sell", "venta", "verkauf", "sale"}:
        return "SELL"
    return None


def _build_row(
    *,
    broker: str,
    asset_id: str,
    side: str,
    trade_date: str,
    quantity: str,
    price: str,
    gross: str,
    fees: str,
    currency: str,
    key_parts: list[str],
) -> dict:
    row = {
        "assetId": asset_id,
        "side": side,
        "tradeDate": trade_date,
        "quantity": quantity,
        "unitPriceOriginal": price,
        "grossAmountOriginal": gross,
        "feesOriginal": fees or "0",
        "currency": currency.upper(),
        "externalId": _stable_external_id(broker, key_parts),
    }
    # Divisa no EUR -> el backend resuelve el cambio con el BCE.
    row["fxSource"] = "USER" if currency.upper() == "EUR" else "ECB"
    if currency.upper() == "EUR":
        row["fxRateToEur"] = "1"
    return row


def _map_generic(content: str) -> list[dict]:
    """CSV genérico con cabeceras equivalentes a las del export propio."""
    rows: list[dict] = []
    for index, raw in enumerate(_read_rows(content)):
        side = _normalize_side(_get(raw, "side", "tipo", "type"))
        asset_id = _get(raw, "assetId", "asset", "symbol", "activo")
        if side is None or not asset_id:
            continue
        quantity = _decimalish(_get(raw, "quantity", "cantidad", "qty", "shares"))
        price = _decimalish(_get(raw, "unitPriceOriginal", "price", "precio"))
        gross = _decimalish(_get(raw, "grossAmountOriginal", "amount", "importe"))
        rows.append(
            _build_row(
                broker="generic",
                asset_id=asset_id,
                side=side,
                trade_date=_get(raw, "tradeDate", "date", "fecha"),
                quantity=quantity,
                price=price,
                gross=gross or (_multiply(quantity, price)),
                fees=_decimalish(_get(raw, "feesOriginal", "fees", "comision", "fee")),
                currency=_get(raw, "currency", "divisa", "moneda") or "EUR",
                key_parts=[_get(raw, "externalId") or str(index), asset_id, side],
            )
        )
    return rows


def _map_trade_republic(content: str) -> list[dict]:
    """Extracto de Trade Republic (columnas en inglés/alemán, importes en EUR)."""
    rows: list[dict] = []
    for index, raw in enumerate(_read_rows(content)):
        side = _normalize_side(_get(raw, "Type", "Transaction", "Tipo"))
        isin = _get(raw, "ISIN", "Instrument", "Asset")
        if side is None or not isin:
            continue
        quantity = _decimalish(_get(raw, "Shares", "Quantity", "Anteile"))
        price = _decimalish(_get(raw, "Price", "Share Price", "Kurs"))
        gross = _decimalish(_get(raw, "Amount", "Total", "Betrag"))
        rows.append(
            _build_row(
                broker="trade_republic",
                asset_id=f"stock:{isin}",
                side=side,
                trade_date=_get(raw, "Date", "Datum", "Timestamp")[:10],
                quantity=quantity,
                price=price,
                gross=gross or _multiply(quantity, price),
                fees=_decimalish(_get(raw, "Fee", "Fees", "Gebühr")),
                currency=_get(raw, "Currency", "Währung") or "EUR",
                key_parts=[_get(raw, "ID", "Reference") or str(index), isin, side],
            )
        )
    return rows


def _map_revolut(content: str) -> list[dict]:
    """Extracto de Revolut (acciones), importes normalmente en USD."""
    rows: list[dict] = []
    for raw in _read_rows(content):
        side = _normalize_side(_get(raw, "Type", "Side"))
        ticker = _get(raw, "Ticker", "Symbol")
        if side is None or not ticker:
            continue
        quantity = _decimalish(_get(raw, "Quantity", "Shares"))
        price = _decimalish(_get(raw, "Price per share", "Price"))
        gross = _decimalish(_get(raw, "Total Amount", "Total", "Amount"))
        rows.append(
            _build_row(
                broker="revolut",
                asset_id=f"stock:{ticker}",
                side=side,
                trade_date=_get(raw, "Date", "Completed Date")[:10],
                quantity=quantity,
                price=price,
                gross=gross or _multiply(quantity, price),
                fees=_decimalish(_get(raw, "Fees", "Commission")),
                currency=_get(raw, "Currency") or "USD",
                key_parts=[ticker, side, _get(raw, "Date", "Completed Date"), quantity],
            )
        )
    return rows


def _multiply(quantity: str, price: str) -> str:
    try:
        from decimal import Decimal

        return format(Decimal(quantity) * Decimal(price), "f")
    except Exception:
        return ""


_MAPPERS = {
    "generic": _map_generic,
    "trade_republic": _map_trade_republic,
    "revolut": _map_revolut,
}


def map_broker_csv(broker: str, content: str) -> list[dict]:
    """Traduce el CSV de un broker soportado a filas canónicas de importación."""
    mapper = _MAPPERS.get(broker)
    if mapper is None:
        raise AppError(
            f"Broker no soportado: {broker}", code="UNSUPPORTED_BROKER", status_code=422
        )
    rows = mapper(content)
    if not rows:
        raise AppError(
            "El CSV no contiene compras/ventas reconocibles para este broker",
            code="NO_OPERATIONS_FOUND",
            status_code=422,
        )
    return rows
