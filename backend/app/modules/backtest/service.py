"""Servicio de backtesting: ejecuta la estrategia sobre las velas almacenadas."""

from __future__ import annotations

from app.modules.backtest import engine
from app.modules.market_data import bars


async def run_backtest(asset_id: str, interval: str = "1m", limit: int = 1000) -> dict:
    candles = await bars.get_bars(asset_id, interval, limit)
    result = engine.run(candles)
    return {
        "symbol": asset_id,
        "interval": interval,
        "candles": len(candles),
        "trades": result.trades,
        "winRate": round(result.win_rate, 2),
        "totalReturnPct": round(result.total_return_pct, 2),
        "avgReturnPct": round(result.avg_return_pct, 2),
        "maxDrawdownPct": round(result.max_drawdown_pct, 2),
    }
