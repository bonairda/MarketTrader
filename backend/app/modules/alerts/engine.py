"""Motor de evaluación de alertas.

Soporta tres tipos de regla:
  - PRICE_CROSS: cruce del precio en vivo por un umbral (evaluado en cada tick).
  - PERCENT_CHANGE: variación porcentual en una ventana de velas por encima del
    umbral (evaluado periódicamente).
  - INDICATOR_CROSS: cruce de un indicador (p. ej. rsi14) por un umbral
    (evaluado periódicamente sobre las velas del timeframe).

El estado (último precio, último valor de indicador y cooldown por regla) se
guarda en Redis, no en memoria: sobrevive a reinicios, es coherente entre
workers y el cooldown se aplica de forma atómica (SET NX EX).

Detectar CRUCE (no nivel) evita disparos repetidos mientras el valor se mantiene
al otro lado del umbral.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.modules.alerts import repository as alerts_repo
from app.modules.dashboard import metrics
from app.modules.market_data import bars, indicators
from app.modules.notifications import dispatcher

log = get_logger("alerts.engine")

_LAST_PRICE_KEY = "alerts:lastprice:"       # + symbol
_LAST_INDICATOR_KEY = "alerts:lastind:"     # + rule_id
_COOLDOWN_KEY = "alerts:cooldown:"          # + rule_id
_STATE_TTL_SECONDS = 3600


class AlertEngine:
    """Evalúa alertas. Estado en Redis (sin estado local salvo la caché de reglas)."""

    def __init__(self) -> None:
        self._rules_by_symbol: dict[str, list[dict]] = {}

    async def refresh_rules(self) -> None:
        """Recarga las reglas activas desde la BD y las agrupa por símbolo."""
        rules = await alerts_repo.list_all_rules(only_enabled=True)
        grouped: dict[str, list[dict]] = {}
        for rule in rules:
            grouped.setdefault(rule["assetId"], []).append(rule)
        self._rules_by_symbol = grouped
        log.info("[ALERT] Reglas activas cargadas: %d", len(rules))

    # ------------------------------------------------------------------
    # PRICE_CROSS: evaluado en cada tick.
    # ------------------------------------------------------------------
    async def on_tick(self, symbol: str, price: float) -> None:
        rules = [
            r for r in self._rules_by_symbol.get(symbol, []) if r["type"] == "PRICE_CROSS"
        ]
        prev = await self._swap_last_price(symbol, price)
        if prev is None or not rules:
            return
        for rule in rules:
            if self._crossed(rule["direction"], rule["threshold"], prev, price):
                if await self._acquire_cooldown(rule):
                    await self._fire(rule, self._price_message(rule, price))

    # ------------------------------------------------------------------
    # PERCENT_CHANGE e INDICATOR_CROSS: evaluados periódicamente.
    # ------------------------------------------------------------------
    async def evaluate_candle_based(self) -> None:
        for symbol, rules in self._rules_by_symbol.items():
            candle_rules = [r for r in rules if r["type"] in ("PERCENT_CHANGE", "INDICATOR_CROSS")]
            if not candle_rules:
                continue
            for rule in candle_rules:
                if rule["type"] == "PERCENT_CHANGE":
                    await self._eval_percent_change(symbol, rule)
                else:
                    await self._eval_indicator_cross(symbol, rule)

    async def _eval_percent_change(self, symbol: str, rule: dict) -> None:
        candles = await bars.get_bars(symbol, rule["timeframe"], limit=1440)
        change = metrics.change_percent(candles)
        if change is None:
            return
        # ABOVE: sube más que el umbral; BELOW: cae más que el umbral (negativo).
        triggered = (
            change >= rule["threshold"]
            if rule["direction"] == "ABOVE"
            else change <= rule["threshold"]
        )
        if triggered and await self._acquire_cooldown(rule):
            arrow = "subido" if rule["direction"] == "ABOVE" else "bajado"
            msg = (
                f"Alerta {symbol.upper()}: ha {arrow} {change:.2f}% "
                f"(umbral {rule['threshold']:g}%)"
            )
            await self._fire(rule, msg)

    async def _eval_indicator_cross(self, symbol: str, rule: dict) -> None:
        indicator_name = rule.get("indicator") or "rsi14"
        candles = await bars.get_bars(symbol, rule["timeframe"], limit=500)
        current = self._latest_indicator(indicator_name, candles)
        if current is None:
            return
        prev = await self._swap_last_indicator(rule["id"], current)
        if prev is None:
            return
        if self._crossed(rule["direction"], rule["threshold"], prev, current):
            if await self._acquire_cooldown(rule):
                arrow = "por encima de" if rule["direction"] == "ABOVE" else "por debajo de"
                msg = (
                    f"Alerta {symbol.upper()}: {indicator_name.upper()} "
                    f"ha cruzado {arrow} {rule['threshold']:g} (valor {current:.2f})"
                )
                await self._fire(rule, msg)

    @staticmethod
    def _latest_indicator(name: str, candles: list[dict]) -> float | None:
        closes = [c["close"] for c in candles]
        if name == "rsi14":
            series = indicators.rsi(closes, 14)
        elif name == "sma20":
            series = indicators.sma(closes, 20)
        elif name == "ema20":
            series = indicators.ema(closes, 20)
        else:
            return None
        for v in reversed(series):
            if v is not None:
                return v
        return None

    # ------------------------------------------------------------------
    # Estado en Redis
    # ------------------------------------------------------------------
    async def _swap_last_price(self, symbol: str, price: float) -> float | None:
        return await self._swap(f"{_LAST_PRICE_KEY}{symbol}", price)

    async def _swap_last_indicator(self, rule_id: str, value: float) -> float | None:
        return await self._swap(f"{_LAST_INDICATOR_KEY}{rule_id}", value)

    async def _swap(self, key: str, value: float) -> float | None:
        redis = get_redis()
        prev = await redis.get(key)
        await redis.set(key, value, ex=_STATE_TTL_SECONDS)
        return float(prev) if prev is not None else None

    async def _acquire_cooldown(self, rule: dict) -> bool:
        cooldown = rule["cooldownSeconds"]
        if cooldown <= 0:
            return True
        redis = get_redis()
        acquired = await redis.set(f"{_COOLDOWN_KEY}{rule['id']}", "1", nx=True, ex=cooldown)
        return bool(acquired)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _crossed(direction: str, threshold: float, prev: float, current: float) -> bool:
        if direction == "ABOVE":
            return prev < threshold <= current
        return prev > threshold >= current

    @staticmethod
    def _price_message(rule: dict, price: float) -> str:
        arrow = "por encima de" if rule["direction"] == "ABOVE" else "por debajo de"
        return (
            f"Alerta {rule['assetId'].upper()}: precio {price:g} "
            f"ha cruzado {arrow} {rule['threshold']:g}"
        )

    async def _fire(self, rule: dict, message: str) -> None:
        log.info("[ALERT] Disparada regla %s: %s", rule["id"], message)
        await dispatcher.notify(message)
        await alerts_repo.mark_triggered(rule["id"])
