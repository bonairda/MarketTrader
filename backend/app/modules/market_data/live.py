"""Acceso al precio en vivo, almacenado en Redis (no en base de datos).

Clave por símbolo: live:price:<symbol> -> hash { price, ts }
Canal pub/sub para difundir ticks a los clientes conectados: live:ticks
"""

from __future__ import annotations

import json

from app.core.redis_client import get_redis

_KEY_PREFIX = "live:price:"

# Canal de Redis Pub/Sub donde el worker publica cada tick y al que se suscribe
# el WebSocket gateway para reenviarlo a los clientes.
LIVE_CHANNEL = "live:ticks"


async def set_live_price(symbol: str, price: float, timestamp_ms: int) -> None:
    r = get_redis()
    await r.hset(
        f"{_KEY_PREFIX}{symbol}",
        mapping={"price": price, "ts": timestamp_ms},
    )
    # Publica el tick para los clientes conectados por WebSocket.
    await r.publish(
        LIVE_CHANNEL,
        json.dumps({"symbol": symbol, "price": price, "ts": timestamp_ms}),
    )


async def get_live_price(symbol: str) -> dict | None:
    r = get_redis()
    data = await r.hgetall(f"{_KEY_PREFIX}{symbol}")
    if not data:
        return None
    return {
        "symbol": symbol,
        "price": float(data["price"]),
        "ts": int(data["ts"]),
    }


async def get_live_prices(symbols: list[str]) -> list[dict]:
    result = []
    for symbol in symbols:
        price = await get_live_price(symbol)
        if price is not None:
            result.append(price)
    return result
