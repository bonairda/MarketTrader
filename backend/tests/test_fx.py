"""Tests del parseo BCE y del servicio de tipos de cambio."""

from datetime import date
from decimal import Decimal

import fakeredis.aioredis
import pytest

from app.modules.fx import ecb
from app.modules.fx import service as fx_service

_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <Cube>
    <Cube time="2025-03-10">
      <Cube currency="USD" rate="1.0850"/>
      <Cube currency="GBP" rate="0.8400"/>
    </Cube>
    <Cube time="2025-03-07">
      <Cube currency="USD" rate="1.0800"/>
    </Cube>
  </Cube>
</gesmes:Envelope>"""


def test_parse_ecb_inverts_to_currency_to_eur():
    rates = ecb.parse_ecb_rates(_XML)
    assert set(rates) == {"2025-03-10", "2025-03-07"}
    usd = rates["2025-03-10"]["USD"]
    assert usd == (Decimal("1") / Decimal("1.0850"))
    assert rates["2025-03-10"]["EUR"] == Decimal("1")


def test_rate_to_eur_handles_eur_parity():
    rates = ecb.parse_ecb_rates(_XML)["2025-03-10"]
    assert ecb.rate_to_eur(rates, "EUR") == Decimal("1")
    assert ecb.rate_to_eur(rates, "usd") == rates["USD"]
    assert ecb.rate_to_eur(rates, "JPY") is None


@pytest.fixture
def fake_redis(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(fx_service, "get_redis", lambda: client)
    return client


async def test_get_rate_eur_is_one_without_network(fake_redis):
    result = await fx_service.get_rate_to_eur("EUR", date(2025, 3, 10))
    assert result["rate"] == "1.000000000000"
    assert result["source"] == "ECB"


async def test_get_rate_uses_feed_and_caches(fake_redis, monkeypatch):
    calls = {"n": 0}

    async def fake_fetch(url):
        calls["n"] += 1
        return ecb.parse_ecb_rates(_XML)

    monkeypatch.setattr(fx_service, "_fetch", fake_fetch)
    first = await fx_service.get_rate_to_eur("USD", date(2025, 3, 10))
    assert first["source"] == "ECB"
    assert first["effectiveDate"] == "2025-03-10"
    # Segunda llamada usa caché: no vuelve a golpear el feed.
    second = await fx_service.get_rate_to_eur("USD", date(2025, 3, 10))
    assert second["rate"] == first["rate"]
    assert calls["n"] == 1


async def test_get_rate_falls_back_to_previous_business_day(fake_redis, monkeypatch):
    async def fake_fetch(url):
        return ecb.parse_ecb_rates(_XML)

    monkeypatch.setattr(fx_service, "_fetch", fake_fetch)
    # Domingo 9/3: usa el viernes 7/3.
    result = await fx_service.get_rate_to_eur("USD", date(2025, 3, 9))
    assert result["effectiveDate"] == "2025-03-07"


async def test_usdt_is_approximated_to_usd(fake_redis, monkeypatch):
    async def fake_fetch(url):
        return ecb.parse_ecb_rates(_XML)

    monkeypatch.setattr(fx_service, "_fetch", fake_fetch)
    result = await fx_service.get_rate_to_eur("USDT", date(2025, 3, 10))
    assert result["source"] == "ECB~USD"
    assert result["requestedCurrency"] == "USDT"


async def test_get_rate_returns_none_without_feed_or_cache(fake_redis, monkeypatch):
    async def empty_fetch(url):
        return {}

    monkeypatch.setattr(fx_service, "_fetch", empty_fetch)
    assert await fx_service.get_rate_to_eur("USD", date(2025, 3, 10)) is None
