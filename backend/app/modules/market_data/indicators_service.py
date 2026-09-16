"""Cálculo de indicadores bajo demanda a partir de las velas almacenadas.

Enfoque F2: se calcula al vuelo desde las velas (no se persiste). Para señales
en tiempo real (F3) se valorará pre-calcular y guardar.
"""

from __future__ import annotations

from app.modules.market_data import bars, indicators


async def compute_indicators(
    asset_id: str, interval: str = "1m", limit: int = 500
) -> dict:
    """Devuelve las velas y un conjunto de indicadores alineados por índice."""
    candles = await bars.get_bars(asset_id, interval, limit)
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    times = [c["openTime"] for c in candles]

    macd_data = indicators.macd(closes)
    bollinger_data = indicators.bollinger(closes)

    return {
        "symbol": asset_id,
        "interval": interval,
        "times": times,
        "indicators": {
            "sma20": indicators.sma(closes, 20),
            "sma50": indicators.sma(closes, 50),
            "ema20": indicators.ema(closes, 20),
            "rsi14": indicators.rsi(closes, 14),
            "atr14": indicators.atr(highs, lows, closes, 14),
            "macd": macd_data["macd"],
            "macdSignal": macd_data["signal"],
            "macdHistogram": macd_data["histogram"],
            "bollingerUpper": bollinger_data["upper"],
            "bollingerMiddle": bollinger_data["middle"],
            "bollingerLower": bollinger_data["lower"],
            "returns": indicators.returns(closes),
        },
    }
