"""Motor de señales por reglas (transparente y explicable).

A partir de indicadores ya calculados produce una señal con:
  - action: BUY | SELL | HOLD | WATCH
  - score: intensidad 0-100 (cuánto empuja la señal)
  - confidence: 0-100 (cuántas reglas coinciden / cuánta evidencia hay)
  - rationale: lista de motivos legibles (por qué se emitió)

Es lógica pura (sin BD ni red) para poder testearla y auditar cada señal.
No es asesoramiento financiero: son señales cuantitativas basadas en reglas.

Enfoque: cada regla aporta "votos" ponderados a favor de comprar o vender y una
frase al rationale. Se agregan los votos y se traduce a una acción.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SignalInputs:
    """Valores actuales de indicadores para evaluar la señal."""

    price: float | None = None
    rsi: float | None = None
    sma20: float | None = None
    sma50: float | None = None
    macd: float | None = None
    macd_signal: float | None = None


@dataclass
class Signal:
    action: str
    score: int
    confidence: int
    rationale: list[str] = field(default_factory=list)


# Pesos de cada regla (cuánto empuja hacia comprar/vender).
_RSI_WEIGHT = 40
_TREND_WEIGHT = 35
_MACD_WEIGHT = 25


def evaluate(inputs: SignalInputs) -> Signal:
    bullish = 0.0
    bearish = 0.0
    rationale: list[str] = []
    rules_evaluated = 0

    # Regla 1: RSI (sobreventa -> comprar, sobrecompra -> vender).
    if inputs.rsi is not None:
        rules_evaluated += 1
        if inputs.rsi <= 30:
            bullish += _RSI_WEIGHT
            rationale.append(f"RSI {inputs.rsi:.0f} en sobreventa (posible rebote)")
        elif inputs.rsi >= 70:
            bearish += _RSI_WEIGHT
            rationale.append(f"RSI {inputs.rsi:.0f} en sobrecompra (posible corrección)")
        else:
            rationale.append(f"RSI {inputs.rsi:.0f} en zona neutral")

    # Regla 2: tendencia por cruce de medias (SMA20 vs SMA50).
    if inputs.sma20 is not None and inputs.sma50 is not None:
        rules_evaluated += 1
        if inputs.sma20 > inputs.sma50:
            bullish += _TREND_WEIGHT
            rationale.append("SMA20 por encima de SMA50 (tendencia alcista)")
        elif inputs.sma20 < inputs.sma50:
            bearish += _TREND_WEIGHT
            rationale.append("SMA20 por debajo de SMA50 (tendencia bajista)")

    # Regla 3: MACD (línea sobre señal -> impulso alcista).
    if inputs.macd is not None and inputs.macd_signal is not None:
        rules_evaluated += 1
        if inputs.macd > inputs.macd_signal:
            bullish += _MACD_WEIGHT
            rationale.append("MACD por encima de su señal (impulso alcista)")
        elif inputs.macd < inputs.macd_signal:
            bearish += _MACD_WEIGHT
            rationale.append("MACD por debajo de su señal (impulso bajista)")

    return _aggregate(bullish, bearish, rules_evaluated, rationale)


def _aggregate(bullish: float, bearish: float, rules: int, rationale: list[str]) -> Signal:
    if rules == 0:
        return Signal(action="HOLD", score=0, confidence=0, rationale=["Sin datos suficientes"])

    net = bullish - bearish
    total = bullish + bearish
    score = int(min(100, abs(net)))
    # Confianza: proporción del peso máximo posible que se ha activado.
    max_possible = _RSI_WEIGHT + _TREND_WEIGHT + _MACD_WEIGHT
    confidence = int(min(100, total / max_possible * 100))

    if net >= 50:
        action = "BUY"
    elif net <= -50:
        action = "SELL"
    elif abs(net) >= 20:
        # Hay sesgo pero no lo bastante fuerte para BUY/SELL: vigilar.
        action = "WATCH"
    else:
        action = "HOLD"

    return Signal(action=action, score=score, confidence=confidence, rationale=rationale)
