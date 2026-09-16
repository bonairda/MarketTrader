"""Endpoints de datos de mercado: precio en vivo (Redis), velas (BD) y stream WS."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.modules.market_data import bars, indicators_service, live
from app.modules.market_data.broadcaster import broadcaster
from app.modules.watchlists import repository as watchlist_repo

log = get_logger("market_data.routes")

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices")
async def live_prices() -> list[dict]:
    """Precio en vivo de todos los activos de la watchlist."""
    symbols = await watchlist_repo.list_items()
    return await live.get_live_prices(symbols)


@router.get("/prices/{symbol}")
async def live_price(symbol: str) -> dict | None:
    return await live.get_live_price(symbol.lower())


@router.get("/bars/{symbol}")
async def get_bars(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=200, le=1000),
) -> list[dict]:
    return await bars.get_bars(symbol.lower(), interval, limit)


@router.get("/indicators/{symbol}")
async def get_indicators(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=500, le=1000),
) -> dict:
    """Indicadores técnicos calculados bajo demanda sobre las velas del activo."""
    return await indicators_service.compute_indicators(symbol.lower(), interval, limit)


@router.websocket("/ws")
async def ws_stream(websocket: WebSocket) -> None:
    """Stream de precios en vivo.

    Usa el broadcaster: una sola suscripción a Redis por proceso y fan-out en
    memoria a todos los clientes. Cada cliente recibe los ticks publicados por
    el worker en `live:ticks`. Mensajes JSON: { "symbol", "price", "ts" }.
    """
    await websocket.accept()
    log.info("[WEBSOCKET] Cliente conectado al stream de precios")
    try:
        async with broadcaster.subscribe() as queue:
            while True:
                data = await queue.get()
                await websocket.send_text(data)
    except WebSocketDisconnect:
        log.info("[WEBSOCKET] Cliente desconectado")
