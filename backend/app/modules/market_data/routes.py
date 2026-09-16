"""Endpoints de datos de mercado: precio en vivo (Redis), velas (BD) y stream WS."""

import json

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.modules.auth import repository as auth_repository
from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.market_data import bars, indicators_service, live
from app.modules.market_data.broadcaster import broadcaster
from app.modules.watchlists import repository as watchlist_repo
from app.providers.symbols import normalize_asset_id

log = get_logger("market_data.routes")

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices")
async def live_prices(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    """Precio en vivo de los activos de la watchlist del usuario."""
    symbols = await watchlist_repo.list_items(user.id)
    return await live.get_live_prices(symbols)


@router.get("/prices/{symbol:path}")
async def live_price(
    symbol: str, user: CurrentUser = Depends(get_current_user)
) -> dict | None:
    return await live.get_live_price(normalize_asset_id(symbol))


@router.get("/bars/{symbol:path}")
async def get_bars(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=200, le=1000),
    user: CurrentUser = Depends(get_current_user),
) -> list[dict]:
    return await bars.get_bars(normalize_asset_id(symbol), interval, limit)


@router.get("/indicators/{symbol:path}")
async def get_indicators(
    symbol: str,
    interval: str = Query(default="1m"),
    limit: int = Query(default=500, le=1000),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Indicadores técnicos calculados bajo demanda sobre las velas del activo."""
    return await indicators_service.compute_indicators(
        normalize_asset_id(symbol), interval, limit
    )


@router.websocket("/ws")
async def ws_stream(websocket: WebSocket) -> None:
    """Stream autenticado, filtrado por la watchlist del usuario.

    El cliente envía el JWT en `?token=...` porque WebSocket en navegador no
    permite una cabecera Authorization arbitraria. El broadcaster sigue siendo
    único por proceso, pero cada conexión solo recibe sus propios símbolos.
    """
    token = websocket.query_params.get("token", "")
    payload = decode_access_token(token) if token else None
    user = (
        await auth_repository.get_by_id(payload["sub"])
        if payload and payload.get("sub")
        else None
    )
    if not user or not user["isActive"]:
        await websocket.close(code=4401, reason="No autenticado")
        return
    symbols = set(await watchlist_repo.list_items(user["id"]))
    await websocket.accept()
    log.info("[WEBSOCKET] Cliente autenticado conectado")
    try:
        async with broadcaster.subscribe() as queue:
            while True:
                data = await queue.get()
                try:
                    tick = json.loads(data)
                except (TypeError, json.JSONDecodeError):
                    continue
                if tick.get("symbol") in symbols:
                    await websocket.send_text(data)
    except WebSocketDisconnect:
        log.info("[WEBSOCKET] Cliente desconectado")
