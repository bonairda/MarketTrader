"""Servicio de señales: combina señal + riesgo para un activo.

Carga las velas, calcula los indicadores actuales, evalúa la señal por reglas y
le adjunta la puntuación de riesgo. Todo bajo demanda (enfoque de F2/F3); si en
el futuro se requieren señales en tiempo real, se pre-calcularán.
"""

from __future__ import annotations

from app.modules.market_data import bars, indicators
from app.modules.signals import engine, risk


def _latest(series: list) -> float | None:
    for v in reversed(series):
        if v is not None:
            return v
    return None


async def get_signal(asset_id: str, interval: str = "1m", limit: int = 500) -> dict:
    candles = await bars.get_bars(asset_id, interval, limit)
    closes = [c["close"] for c in candles]

    macd_data = indicators.macd(closes)
    inputs = engine.SignalInputs(
        price=_latest(closes),
        rsi=_latest(indicators.rsi(closes, 14)),
        sma20=_latest(indicators.sma(closes, 20)),
        sma50=_latest(indicators.sma(closes, 50)),
        macd=_latest(macd_data["macd"]),
        macd_signal=_latest(macd_data["signal"]),
    )

    signal = engine.evaluate(inputs)
    risk_score = risk.score(candles)

    return {
        "symbol": asset_id,
        "interval": interval,
        "action": signal.action,
        "score": signal.score,
        "confidence": signal.confidence,
        "rationale": signal.rationale,
        "risk": {
            "score": risk_score.score,
            "level": risk_score.level,
            "factors": risk_score.factors,
        },
    }
