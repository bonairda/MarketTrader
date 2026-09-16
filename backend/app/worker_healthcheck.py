"""Comando de healthcheck del worker (`python -m app.worker_healthcheck`)."""

import asyncio

from app.core.redis_client import close_redis
from app.core.worker_health import worker_is_healthy


async def main() -> int:
    try:
        return 0 if await worker_is_healthy() else 1
    finally:
        await close_redis()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
