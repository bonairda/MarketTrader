"""Router raíz de la API. Agrupa los routers de cada módulo."""

from fastapi import APIRouter

from app.modules.alerts.routes import router as alerts_router
from app.modules.auth.routes import router as auth_router
from app.modules.backtest.routes import router as backtest_router
from app.modules.dashboard.routes import router as dashboard_router
from app.modules.market_data.routes import router as market_router
from app.modules.operations.routes import router as operations_router
from app.modules.portfolio.routes import router as portfolio_router
from app.modules.signals.routes import router as signals_router
from app.modules.watchlists.routes import router as watchlist_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(market_router)
api_router.include_router(watchlist_router)
api_router.include_router(alerts_router)
api_router.include_router(dashboard_router)
api_router.include_router(signals_router)
api_router.include_router(backtest_router)
api_router.include_router(portfolio_router)
api_router.include_router(operations_router)
