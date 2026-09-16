"""Servicio de tipos de cambio a EUR con caché Redis y fallback.

Resuelve `divisa -> EUR` (1 divisa = N EUR) para una fecha dada usando el feed
del BCE. El resultado se cachea en Redis para no golpear el BCE en cada alta de
operación. Si el BCE no responde y no hay caché, devuelve None: el llamante debe
entonces exigir la tasa manual.

Notas:
- EUR se resuelve a 1 sin red.
- USDT (cripto estable) se aproxima a USD, marcándolo en la fuente.
- El BCE solo publica días hábiles; para fines de semana/festivos se usa el
  último día disponible <= fecha pedida dentro del feed de 90 días.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from xml.etree.ElementTree import ParseError

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.modules.fx import ecb

log = get_logger("fx.service")

_CACHE_PREFIX = "fx:ecb:"
# Divisas que aproximamos a otra referencia del BCE.
_ALIASES = {"USDT": "USD", "USDC": "USD"}


def _cache_key(day: str) -> str:
    return f"{_CACHE_PREFIX}{day}"


async def _load_day_from_cache(day: str) -> dict[str, Decimal] | None:
    cached = await get_redis().get(_cache_key(day))
    if not cached:
        return None
    try:
        raw = json.loads(cached)
    except (TypeError, json.JSONDecodeError):
        return None
    return {code: Decimal(value) for code, value in raw.items()}


async def _store_days(rates_by_day: dict[str, dict[str, Decimal]]) -> None:
    redis = get_redis()
    for day, rates in rates_by_day.items():
        payload = json.dumps({code: format(value, "f") for code, value in rates.items()})
        await redis.set(_cache_key(day), payload, ex=settings.ecb_fx_cache_ttl_seconds)


async def _fetch(url: str) -> dict[str, dict[str, Decimal]]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(url)
            res.raise_for_status()
            return ecb.parse_ecb_rates(res.text)
    except (httpx.HTTPError, ParseError, ValueError) as exc:
        log.warning("[FX] No se pudo obtener el feed del BCE: %s", exc)
        return {}


async def _resolve_day(target: date) -> tuple[str, dict[str, Decimal]] | None:
    """Devuelve el día efectivo (<= target) y sus tasas, con caché y fallback."""
    iso = target.isoformat()
    cached = await _load_day_from_cache(iso)
    if cached:
        return iso, cached

    # El feed de 90 días permite resolver fechas recientes y días no hábiles.
    history = await _fetch(settings.ecb_fx_history_url)
    if not history:
        history = await _fetch(settings.ecb_fx_daily_url)
    if history:
        await _store_days(history)
        available = sorted(day for day in history if day <= iso)
        if available:
            effective = available[-1]
            return effective, history[effective]

    # Último recurso: cualquier día cacheado previo.
    return None


async def get_rate_to_eur(currency: str, on: date) -> dict | None:
    """Cambio divisa->EUR para una fecha. None si no se puede resolver.

    Devuelve {rate(str), source, effectiveDate, requestedCurrency}.
    """
    requested = currency.strip().upper()
    lookup = _ALIASES.get(requested, requested)

    if lookup == "EUR":
        return {
            "rate": "1.000000000000",
            "source": "ECB",
            "effectiveDate": on.isoformat(),
            "requestedCurrency": requested,
        }

    resolved = await _resolve_day(on)
    if not resolved:
        return None
    effective_day, rates = resolved
    rate = ecb.rate_to_eur(rates, lookup)
    if rate is None:
        return None
    source = "ECB" if lookup == requested else f"ECB~{lookup}"
    return {
        "rate": format(rate, "f"),
        "source": source,
        "effectiveDate": effective_day,
        "requestedCurrency": requested,
    }
