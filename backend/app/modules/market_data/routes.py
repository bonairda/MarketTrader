"""Endpoints de datos de mercado: precio en vivo (Redis), velas (BD) y stream WS."""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.modules.market_data import bars, live
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


@router.websocket("/ws")
async def ws_stream(websocket: WebSocket) -> None:
    """Stream de precios en vivo.

    Reenvía a cada cliente los ticks que el worker publica en el canal Redis
    `live:ticks`. Los mensajes son JSON: { "symbol", "price", "ts" }.
    """
    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(live.LIVE_CHANNEL)
    log.info("[WEBSOCKET] Cliente conectado al stream de precios")
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        log.info("[WEBSOCKET] Cliente desconectado")
    finally:
        await pubsub.unsubscribe(live.LIVE_CHANNEL)
        await pubsub.aclose()
