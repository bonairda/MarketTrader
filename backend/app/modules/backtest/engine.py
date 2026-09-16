"""Motor de backtesting de la estrategia de señales (puro y sin lookahead).

Recorre las velas en orden y, en cada paso, evalúa la señal usando SOLO los
datos disponibles hasta ese momento (nunca el futuro). Simula una estrategia
long-only sencilla:
  - Entra (compra) cuando la señal es BUY y no hay posición abierta.
  - Sale (vende) cuando la señal es SELL y hay posición abierta.
Cierra cualquier posición abierta al final para poder medir el resultado.

Devuelve métricas de la estrategia: retorno total, nº de operaciones, win rate,
retorno medio por operación y máximo drawdown de la curva de equity.

Es una herramienta de medición, no una promesa de resultados. No incluye
comisiones ni slippage (se puede añadir después).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.market_data import indicators
from app.modules.signals import engine as signal_engine

# Nº mínimo de velas antes de empezar a operar (para que los indicadores lentos,
# como SMA50 o MACD, tengan datos).
_WARMUP = 50


@dataclass
class Trade:
    entry_index: int
    entry_price: float
    exit_index: int
    exit_price: float

    @property
    def return_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        return (self.exit_price - self.entry_price) / self.entry_price * 100


@dataclass
class BacktestResult:
    trades: int
    win_rate: float          # % de operaciones ganadoras
    total_return_pct: float  # retorno compuesto de la estrategia
    avg_return_pct: float    # retorno medio por operación
    max_drawdown_pct: float  # peor caída de la curva de equity
    detail: list[Trade] = field(default_factory=list)


def _latest(series: list) -> float | None:
    for v in reversed(series):
        if v is not None:
            return v
    return None


def _signal_action_at(closes_so_far: list[float]) -> str:
    """Señal usando solo los cierres hasta el momento (sin lookahead)."""
    macd_data = indicators.macd(closes_so_far)
    inputs = signal_engine.SignalInputs(
        price=_latest(closes_so_far),
        rsi=_latest(indicators.rsi(closes_so_far, 14)),
        sma20=_latest(indicators.sma(closes_so_far, 20)),
        sma50=_latest(indicators.sma(closes_so_far, 50)),
        macd=_latest(macd_data["macd"]),
        macd_signal=_latest(macd_data["signal"]),
    )
    return signal_engine.evaluate(inputs).action


def run(candles: list[dict]) -> BacktestResult:
    closes = [c["close"] for c in candles]
    if len(closes) <= _WARMUP:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0)

    trades: list[Trade] = []
    in_position = False
    entry_index = 0
    entry_price = 0.0

    for i in range(_WARMUP, len(closes)):
        action = _signal_action_at(closes[: i + 1])
        price = closes[i]

        if not in_position and action == "BUY":
            in_position = True
            entry_index = i
            entry_price = price
        elif in_position and action == "SELL":
            trades.append(Trade(entry_index, entry_price, i, price))
            in_position = False

    # Cerrar posición abierta con el último precio.
    if in_position:
        trades.append(Trade(entry_index, entry_price, len(closes) - 1, closes[-1]))

    return _summarize(trades)


def _summarize(trades: list[Trade]) -> BacktestResult:
    if not trades:
        return BacktestResult(0, 0.0, 0.0, 0.0, 0.0)

    wins = sum(1 for t in trades if t.return_pct > 0)
    returns = [t.return_pct for t in trades]

    # Retorno compuesto: encadenar (1 + r) de cada operación.
    equity = 1.0
    curve = [equity]
    for r in returns:
        equity *= 1 + r / 100
        curve.append(equity)

    total_return = (equity - 1) * 100
    avg_return = sum(returns) / len(returns)
    max_dd = _max_drawdown(curve)

    return BacktestResult(
        trades=len(trades),
        win_rate=wins / len(trades) * 100,
        total_return_pct=total_return,
        avg_return_pct=avg_return,
        max_drawdown_pct=max_dd,
        detail=trades,
    )


def _max_drawdown(curve: list[float]) -> float:
    peak = curve[0]
    worst = 0.0
    for value in curve:
        if value > peak:
            peak = value
        if peak > 0:
            worst = max(worst, (peak - value) / peak * 100)
    return worst
