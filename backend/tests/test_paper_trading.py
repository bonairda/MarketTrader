"""Tests del servicio de paper trading (sin red real)."""

import pytest

from app.core.errors import AppError
from app.modules.paper_trading import service


def test_status_reports_enabled_flag(monkeypatch):
    monkeypatch.setattr(service.alpaca, "is_enabled", lambda: False)
    assert service.status() == {"enabled": False, "mode": "paper"}


async def test_submit_requires_enabled(monkeypatch):
    monkeypatch.setattr(service.alpaca, "is_enabled", lambda: False)
    with pytest.raises(AppError) as exc:
        await service.submit_order("stock:AAPL", "1", "BUY", confirm=True)
    assert exc.value.code == "PAPER_TRADING_DISABLED"


async def test_submit_requires_confirmation(monkeypatch):
    monkeypatch.setattr(service.alpaca, "is_enabled", lambda: True)
    with pytest.raises(AppError) as exc:
        await service.submit_order("stock:AAPL", "1", "BUY", confirm=False)
    assert exc.value.code == "CONFIRMATION_REQUIRED"


async def test_submit_rejects_non_stock(monkeypatch):
    monkeypatch.setattr(service.alpaca, "is_enabled", lambda: True)
    with pytest.raises(AppError) as exc:
        await service.submit_order("btcusdt", "1", "BUY", confirm=True)
    assert exc.value.code == "UNSUPPORTED_PAPER_ASSET"


async def test_submit_forwards_ticker_and_returns_summary(monkeypatch):
    captured = {}

    async def fake_submit(symbol, qty, side):
        captured.update(symbol=symbol, qty=qty, side=side)
        return {"id": "o1", "status": "accepted", "submitted_at": "2025-01-01T10:00:00Z"}

    monkeypatch.setattr(service.alpaca, "is_enabled", lambda: True)
    monkeypatch.setattr(service.alpaca, "submit_order", fake_submit)

    result = await service.submit_order("stock:AAPL", "3", "BUY", confirm=True)
    assert captured["symbol"] == "AAPL"
    assert result["status"] == "accepted"
    assert result["side"] == "BUY"
