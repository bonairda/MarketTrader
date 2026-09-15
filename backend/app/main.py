"""Entrypoint de la API FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.core.db import init_db
from app.core.logging import get_logger, setup_logging
from app.core.redis_client import close_redis

setup_logging()
log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("[INFO] Inicializando esquema de base de datos")
    await init_db()
    yield
    await close_redis()


app = FastAPI(title="MarketTracker API", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
