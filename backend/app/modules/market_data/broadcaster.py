"""Broadcaster de ticks en vivo.

Mantiene UNA sola suscripción al canal Redis `live:ticks` por proceso de API y
reparte (fan-out) cada mensaje a todas las conexiones WebSocket activas mediante
colas asyncio. Así, con N clientes conectados solo hay 1 suscripción a Redis en
lugar de N, lo que escala mucho mejor.

Uso:
    broadcaster = LiveBroadcaster()
    await broadcaster.start()          # al arrancar la app (lifespan)
    async with broadcaster.subscribe() as queue:   # por cada cliente WS
        msg = await queue.get()
    ...
    await broadcaster.stop()           # al apagar la app
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.modules.market_data import live

log = get_logger("market_data.broadcaster")

# Tamaño máximo de la cola por cliente. Si un cliente es lento y se llena, se
# descartan los mensajes más antiguos para no acumular memoria (backpressure).
_CLIENT_QUEUE_MAXSIZE = 100


class LiveBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            log.info("[WEBSOCKET] Broadcaster iniciado")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None
            log.info("[WEBSOCKET] Broadcaster detenido")

    async def _run(self) -> None:
        """Única suscripción a Redis; reparte cada mensaje a los suscriptores."""
        redis = get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(live.LIVE_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                self._fan_out(message["data"])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(live.LIVE_CHANNEL)
            await pubsub.aclose()

    def _fan_out(self, data: str) -> None:
        for queue in self._subscribers:
            if queue.full():
                # Cliente lento: descarta el mensaje más antiguo.
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(data)

    @asynccontextmanager
    async def subscribe(self):
        """Registra un cliente y devuelve su cola; se limpia al salir."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=_CLIENT_QUEUE_MAXSIZE)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)


# Instancia única compartida por la app (arrancada/parada en el lifespan).
broadcaster = LiveBroadcaster()
