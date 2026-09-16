"""Parseo puro del feed de tipos de cambio del BCE.

El BCE publica, por fecha, el cambio de referencia EUR -> divisa
(1 EUR = N divisa). MarketTracker necesita divisa -> EUR (1 divisa = N EUR),
que es el inverso. Este módulo no hace red ni toca Redis: solo transforma el
XML en un mapa de tasas `divisa -> EUR` en Decimal, para que sea testeable.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

# Divisas que ya están, por definición, en EUR o se tratan a la par.
_EUR_PARITY = {"EUR"}


def parse_ecb_rates(xml_text: str) -> dict[str, dict[str, Decimal]]:
    """Devuelve {fecha_iso: {divisa: cambio_a_eur}} a partir del XML del BCE.

    Incluye siempre EUR->EUR = 1. Ignora entradas con valores no numéricos.
    """
    root = ElementTree.fromstring(xml_text)
    result: dict[str, dict[str, Decimal]] = {}
    # El XML usa el namespace gesmes/eurofxref; buscamos por sufijo de tag para
    # no depender del prefijo declarado.
    for cube in root.iter():
        if not cube.tag.endswith("Cube"):
            continue
        day = cube.attrib.get("time")
        if not day:
            continue
        rates: dict[str, Decimal] = {"EUR": Decimal("1")}
        for entry in cube:
            currency = entry.attrib.get("currency")
            raw = entry.attrib.get("rate")
            if not currency or raw is None:
                continue
            try:
                eur_to_currency = Decimal(raw)
            except (InvalidOperation, TypeError):
                continue
            if eur_to_currency <= 0:
                continue
            # Inversión: 1 divisa = 1 / (EUR->divisa) EUR.
            rates[currency.upper()] = Decimal("1") / eur_to_currency
        if len(rates) > 1:
            result[day] = rates
    return result


def rate_to_eur(rates: dict[str, Decimal], currency: str) -> Decimal | None:
    """Cambio de una divisa a EUR para un día ya resuelto."""
    code = currency.strip().upper()
    if code in _EUR_PARITY:
        return Decimal("1")
    return rates.get(code)
