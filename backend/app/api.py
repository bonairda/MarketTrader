"""Router raíz de la API. Agrupa los routers de cada módulo."""

from fastapi import APIRouter

from app.modules.alerts.routes import router as alerts_router
from app.modules.market_data.routes import router as market_router
from app.modules.watchlists.routes import router as watchlist_router

api_router = APIRouter()
api_router.include_router(market_router)
api_router.include_router(watchlist_router)
api_router.include_router(alerts_router)
