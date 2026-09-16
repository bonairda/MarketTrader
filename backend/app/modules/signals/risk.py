"""Puntuación de riesgo de un activo (0-100), pura y explicable.

Combina factores calculables desde las velas:
  - Volatilidad reciente (desviación de retornos).
  - Máximo drawdown en la ventana.
Devuelve un score 0-100 (mayor = más riesgo) y una explicación de los factores.

No es una medida de riesgo regulada; es una heurística para acompañar a las
señales y que el usuario nunca vea una recomendación sin su riesgo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.dashboard import metrics


@dataclass
class RiskScore:
    score: int  # 0-100
    level: str  # LOW | MEDIUM | HIGH
    factors: list[str] = field(default_factory=list)


def max_drawdown(candles: list[dict]) -> float | None:
    """Máxima caída porcentual desde un pico previo (valor positivo, en %)."""
    if len(candles) < 2:
        return None
    closes = [c["close"] for c in candles]
    peak = closes[0]
    worst = 0.0
    for price in closes:
        if price > peak:
            peak = price
        if peak > 0:
            drop = (peak - price) / peak * 100
            worst = max(worst, drop)
    return worst


def score(candles: list[dict]) -> RiskScore:
    if len(candles) < 3:
        return RiskScore(score=0, level="LOW", factors=["Sin datos suficientes"])

    factors: list[str] = []
    total = 0.0

    vol = metrics.volatility(candles)
    if vol is not None:
        # Volatilidad por vela; se escala para que ~2% de desviación sea alto.
        vol_component = min(60.0, vol * 30)
        total += vol_component
        factors.append(f"Volatilidad {vol:.2f}% por vela")

    dd = max_drawdown(candles)
    if dd is not None:
        # Drawdown; ~20% de caída satura el componente.
        dd_component = min(40.0, dd * 2)
        total += dd_component
        factors.append(f"Drawdown máximo {dd:.1f}%")

    final = int(min(100, total))
    if final >= 66:
        level = "HIGH"
    elif final >= 33:
        level = "MEDIUM"
    else:
        level = "LOW"
    return RiskScore(score=final, level=level, factors=factors)
