"""Métricas resumidas de un activo a partir de sus velas.

Funciones puras (sin BD ni red) para poder testearlas con facilidad.
Todas reciben las velas en orden cronológico ascendente (como las devuelve
`bars.get_bars`): [{open, high, low, close, ...}, ...].
"""

from __future__ import annotations


def change_percent(candles: list[dict]) -> float | None:
    """Variación porcentual entre la apertura de la primera vela y el último cierre."""
    if len(candles) < 1:
        return None
    first_open = candles[0]["open"]
    last_close = candles[-1]["close"]
    if first_open == 0:
        return None
    return (last_close - first_open) / first_open * 100


def high_low(candles: list[dict]) -> tuple[float | None, float | None]:
    """Máximo y mínimo de la ventana."""
    if not candles:
        return None, None
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    return max(highs), min(lows)


def volatility(candles: list[dict]) -> float | None:
    """Desviación estándar de los retornos porcentuales entre cierres."""
    if len(candles) < 3:
        return None
    closes = [c["close"] for c in candles]
    rets: list[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev != 0:
            rets.append((closes[i] - prev) / prev * 100)
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    variance = sum((r - mean) ** 2 for r in rets) / len(rets)
    return variance**0.5


def summarize(symbol: str, candles: list[dict], last_price: float | None) -> dict:
    """Resumen de un activo para el dashboard."""
    high, low = high_low(candles)
    return {
        "symbol": symbol,
        "price": last_price if last_price is not None else (candles[-1]["close"] if candles else None),
        "changePercent": change_percent(candles),
        "high": high,
        "low": low,
        "volatility": volatility(candles),
    }


def top_movers(summaries: list[dict], limit: int = 5) -> dict:
    """Mayores subidas y bajadas por changePercent (ignora los que no lo tienen)."""
    with_change = [s for s in summaries if s.get("changePercent") is not None]
    ascending = sorted(with_change, key=lambda s: s["changePercent"])
    gainers = list(reversed(ascending[-limit:])) if ascending else []
    losers = ascending[:limit]
    return {"gainers": gainers, "losers": losers}


def most_volatile(summaries: list[dict], limit: int = 5) -> list[dict]:
    """Activos con mayor volatilidad."""
    with_vol = [s for s in summaries if s.get("volatility") is not None]
    return sorted(with_vol, key=lambda s: s["volatility"], reverse=True)[:limit]
