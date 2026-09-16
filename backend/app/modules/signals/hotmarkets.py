"""Detección de "mercados llamativos" (hot markets).

Busca anomalías en las velas recientes de un activo que merezcan una alerta
proactiva, aunque el usuario no tenga una regla configurada:
  - Movimiento fuerte: la última vela se mueve muchas desviaciones respecto a lo
    normal (retorno atípico).
  - Volumen inusual: volumen muy por encima de su media reciente.
  - Ruptura: el precio supera el máximo (o pierde el mínimo) de la ventana.

Es lógica pura y explicable: devuelve el motivo si detecta algo, o None.
"""

from __future__ import annotations

from dataclasses import dataclass

# Umbrales (conservadores para no spamear).
_MOVE_STD_MULTIPLE = 3.0     # retorno de la última vela > 3 desviaciones
_VOLUME_MULTIPLE = 3.0       # volumen > 3x la media
_MIN_CANDLES = 20


@dataclass
class HotMarket:
    symbol: str
    reason: str
    detail: str


def detect(symbol: str, candles: list[dict]) -> HotMarket | None:
    if len(candles) < _MIN_CANDLES:
        return None

    closes = [c["close"] for c in candles]

    move = _detect_abnormal_move(closes)
    if move is not None:
        return HotMarket(symbol, "MOVE", move)

    volume = _detect_volume_spike(candles)
    if volume is not None:
        return HotMarket(symbol, "VOLUME", volume)

    breakout = _detect_breakout(candles)
    if breakout is not None:
        return HotMarket(symbol, "BREAKOUT", breakout)

    return None


def _detect_abnormal_move(closes: list[float]) -> str | None:
    rets = _returns(closes)
    if len(rets) < 3:
        return None
    body = rets[:-1]  # historial sin el último para medir "lo normal"
    last = rets[-1]
    mean = sum(body) / len(body)
    variance = sum((r - mean) ** 2 for r in body) / len(body)
    std = variance**0.5
    if std == 0:
        return None
    deviations = abs(last - mean) / std
    if deviations >= _MOVE_STD_MULTIPLE:
        direction = "subida" if last > 0 else "bajada"
        return f"Movimiento atípico: {direction} de {last:.2f}% ({deviations:.1f} desviaciones)"
    return None


def _detect_volume_spike(candles: list[dict]) -> str | None:
    volumes = [c.get("volume") for c in candles]
    if any(v is None for v in volumes):
        return None
    body = volumes[:-1]
    last = volumes[-1]
    avg = sum(body) / len(body)
    if avg <= 0:
        return None
    ratio = last / avg
    if ratio >= _VOLUME_MULTIPLE:
        return f"Volumen inusual: {ratio:.1f}x su media reciente"
    return None


def _detect_breakout(candles: list[dict]) -> str | None:
    highs = [c["high"] for c in candles[:-1]]
    lows = [c["low"] for c in candles[:-1]]
    last = candles[-1]["close"]
    if last > max(highs):
        return f"Ruptura de máximos: precio {last:g} supera el máximo reciente"
    if last < min(lows):
        return f"Ruptura de mínimos: precio {last:g} pierde el mínimo reciente"
    return None


def _returns(closes: list[float]) -> list[float]:
    rets: list[float] = []
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        if prev != 0:
            rets.append((closes[i] - prev) / prev * 100)
    return rets
