"""Entrypoint de la API FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.bootstrap import ensure_superadmin
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.health import health_report
from app.core.logging import get_logger, setup_logging
from app.core.redis_client import close_redis
from app.modules.market_data.broadcaster import broadcaster

setup_logging()
log = get_logger("main")
settings.assert_safe_for_production()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El esquema se aplica con Alembic al arrancar el contenedor (ver docker-compose).
    log.info("[INFO] API iniciando")
    await ensure_superadmin()
    await broadcaster.start()
    yield
    await broadcaster.stop()
    await close_redis()


app = FastAPI(
    title="MarketTracker API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials="*" not in settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> JSONResponse:
    """Salud del servicio y sus dependencias. 503 si alguna dependencia falla."""
    report = await health_report()
    status_code = 200 if report["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=report)


@app.get("/health/system", tags=["health"])
async def system_health() -> JSONResponse:
    """Salud integral: API, DB, Redis y heartbeat del worker."""
    report = await health_report(include_worker=True)
    status_code = 200 if report["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=report)
