"""Motor de evaluación de alertas de precio.

Se alimenta de cada tick del worker. Para cada regla activa del símbolo detecta
un CRUCE del umbral (no un simple "está por encima"), respeta un cooldown por
regla y dispara la notificación.

El estado (último precio por símbolo y cooldown por regla) se guarda en Redis,
no en memoria. Así:
  - sobrevive a reinicios del worker,
  - es coherente si hubiera varios workers,
  - el cooldown se aplica de forma atómica (SET NX EX), evitando disparos
    duplicados por condiciones de carrera.

Detectar cruce (y no nivel) evita disparos repetidos mientras el precio se
mantiene al otro lado del umbral.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.modules.alerts import repository as alerts_repo
from app.modules.notifications import dispatcher

log = get_logger("alerts.engine")

_LAST_PRICE_KEY = "alerts:lastprice:"  # + symbol
_COOLDOWN_KEY = "alerts:cooldown:"     # + rule_id
# El último precio expira si el símbolo deja de operar mucho tiempo, para no
# arrastrar un valor obsoleto que provoque un "cruce" falso al volver.
_LAST_PRICE_TTL_SECONDS = 3600


class AlertEngine:
    """Evalúa alertas de precio. Estado en Redis (sin estado local)."""

    def __init__(self) -> None:
        self._rules_by_symbol: dict[str, list[dict]] = {}

    async def refresh_rules(self) -> None:
        """Recarga las reglas activas desde la BD y las agrupa por símbolo."""
        rules = await alerts_repo.list_rules(only_enabled=True)
        grouped: dict[str, list[dict]] = {}
        for rule in rules:
            grouped.setdefault(rule["assetId"], []).append(rule)
        self._rules_by_symbol = grouped
        log.info("[ALERT] Reglas activas cargadas: %d", len(rules))

    async def on_tick(self, symbol: str, price: float) -> None:
        rules = self._rules_by_symbol.get(symbol)
        prev = await self._swap_last_price(symbol, price)
        if prev is None or not rules:
            return  # necesitamos dos precios y al menos una regla

        for rule in rules:
            if self._crossed(rule, prev, price) and await self._acquire_cooldown(rule):
                await self._fire(rule, price)

    async def _swap_last_price(self, symbol: str, price: float) -> float | None:
        """Guarda el nuevo precio y devuelve el anterior (o None si no había)."""
        redis = get_redis()
        key = f"{_LAST_PRICE_KEY}{symbol}"
        prev = await redis.get(key)
        await redis.set(key, price, ex=_LAST_PRICE_TTL_SECONDS)
        return float(prev) if prev is not None else None

    @staticmethod
    def _crossed(rule: dict, prev: float, current: float) -> bool:
        threshold = rule["threshold"]
        if rule["direction"] == "ABOVE":
            return prev < threshold <= current
        # BELOW
        return prev > threshold >= current

    async def _acquire_cooldown(self, rule: dict) -> bool:
        """Marca el cooldown de la regla de forma atómica.

        Devuelve True solo si el cooldown estaba libre (y lo reserva). Si otra
        evaluación ya lo tenía, devuelve False y no se dispara.
        """
        cooldown = rule["cooldownSeconds"]
        if cooldown <= 0:
            return True
        redis = get_redis()
        # NX: solo si no existe. EX: expira tras el cooldown.
        acquired = await redis.set(
            f"{_COOLDOWN_KEY}{rule['id']}", "1", nx=True, ex=cooldown
        )
        return bool(acquired)

    async def _fire(self, rule: dict, price: float) -> None:
        arrow = "por encima de" if rule["direction"] == "ABOVE" else "por debajo de"
        message = (
            f"Alerta {rule['assetId'].upper()}: precio {price:g} "
            f"ha cruzado {arrow} {rule['threshold']:g}"
        )
        log.info("[ALERT] Disparada regla %s: %s", rule["id"], message)
        await dispatcher.notify(message)
        await alerts_repo.mark_triggered(rule["id"])
