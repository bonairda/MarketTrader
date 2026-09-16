"""Indicadores técnicos, cálculo puro sobre listas de precios (velas).

Implementación en Python puro (sin pandas) para mantener la imagen ligera y las
funciones fácilmente testeables. Todas las funciones reciben una lista de
valores en orden cronológico ascendente y devuelven listas de la misma longitud,
usando None donde el indicador aún no tiene suficientes datos.
"""

from __future__ import annotations


def sma(values: list[float], period: int) -> list[float | None]:
    """Media móvil simple."""
    if period <= 0:
        raise ValueError("period debe ser > 0")
    result: list[float | None] = [None] * len(values)
    window_sum = 0.0
    for i, v in enumerate(values):
        window_sum += v
        if i >= period:
            window_sum -= values[i - period]
        if i >= period - 1:
            result[i] = window_sum / period
    return result


def ema(values: list[float], period: int) -> list[float | None]:
    """Media móvil exponencial. Se siembra con la SMA del primer periodo."""
    if period <= 0:
        raise ValueError("period debe ser > 0")
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result
    k = 2 / (period + 1)
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        result[i] = prev
    return result


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    """Índice de fuerza relativa (RSI) por el método de Wilder."""
    if period <= 0:
        raise ValueError("period debe ser > 0")
    result: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return result

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        change = values[i] - values[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    result[period] = _rsi_from_averages(avg_gain, avg_loss)

    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = change if change > 0 else 0.0
        loss = -change if change < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        result[i] = _rsi_from_averages(avg_gain, avg_loss)
    return result


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, list[float | None]]:
    """MACD = EMA(fast) - EMA(slow); signal = EMA(MACD); histogram = MACD - signal."""
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    macd_line: list[float | None] = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(ema_fast, ema_slow, strict=False)
    ]
    # Señal: EMA del MACD sobre la parte no nula.
    macd_defined = [v for v in macd_line if v is not None]
    signal_defined = ema(macd_defined, signal)
    # Reubicar la señal alineada con macd_line.
    signal_line: list[float | None] = [None] * len(values)
    offset = len(values) - len(macd_defined)
    for i, v in enumerate(signal_defined):
        signal_line[offset + i] = v
    histogram: list[float | None] = [
        (m - s) if (m is not None and s is not None) else None
        for m, s in zip(macd_line, signal_line, strict=False)
    ]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def true_range(highs: list[float], lows: list[float], closes: list[float]) -> list[float]:
    """Rango verdadero (TR) por vela."""
    tr: list[float] = []
    for i in range(len(closes)):
        if i == 0:
            tr.append(highs[i] - lows[i])
        else:
            prev_close = closes[i - 1]
            tr.append(
                max(
                    highs[i] - lows[i],
                    abs(highs[i] - prev_close),
                    abs(lows[i] - prev_close),
                )
            )
    return tr


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> list[float | None]:
    """Average True Range (media simple del TR sobre `period`)."""
    tr = true_range(highs, lows, closes)
    return sma(tr, period)


def bollinger(
    values: list[float], period: int = 20, num_std: float = 2.0
) -> dict[str, list[float | None]]:
    """Bandas de Bollinger: media SMA y bandas a num_std desviaciones."""
    middle = sma(values, period)
    upper: list[float | None] = [None] * len(values)
    lower: list[float | None] = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        mean = middle[i]
        variance = sum((x - mean) ** 2 for x in window) / period
        std = variance**0.5
        upper[i] = mean + num_std * std
        lower[i] = mean - num_std * std
    return {"middle": middle, "upper": upper, "lower": lower}


def returns(values: list[float]) -> list[float | None]:
    """Rendimiento porcentual respecto a la vela anterior."""
    result: list[float | None] = [None] * len(values)
    for i in range(1, len(values)):
        prev = values[i - 1]
        if prev != 0:
            result[i] = (values[i] - prev) / prev * 100
    return result
