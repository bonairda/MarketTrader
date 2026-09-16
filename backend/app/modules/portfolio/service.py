"""Servicio de cartera: valora las posiciones con el precio en vivo."""

from __future__ import annotations

from app.modules.market_data import live
from app.modules.portfolio import repository, valuation


async def get_portfolio(user_id: str) -> dict:
    positions = await repository.list_positions(user_id)
    valued: list[dict] = []
    for pos in positions:
        live_price = await live.get_live_price(pos["assetId"])
        price = live_price["price"] if live_price else None
        v = valuation.value_position(pos["quantity"], pos["averagePrice"], price)
        valued.append({**pos, "currentPrice": price, **v})

    summary = valuation.summarize(valued)
    return {"positions": valued, "summary": summary}
