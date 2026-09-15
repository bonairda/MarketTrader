"""Motor de evaluación de alertas de precio.

Se alimenta de cada tick del worker. Para cada regla activa del símbolo detecta
un CRUCE del umbral (no un simple "está por encima"), respeta un cooldown por
regla y dispara la notificación.

Detectar cruce (y no nivel) evita disparos repetidos mientras el precio se
mantiene al otro lado del umbral.
"""

from __future__ import annotations

import time

from app.core.logging import get_logger
from app.modules.alerts import repository as alerts_repo
from app.modules.notifications import telegram

log = get_logger("alerts.engine")


class AlertEngine:
    """Evalúa alertas de precio. Una instancia por proceso worker."""

    def __init__(self) -> None:
        # Último precio visto por símbolo (para detectar el cruce).
        self._last_price: dict[str, float] = {}
        # Momento del último disparo por regla (epoch s), para el cooldown.
        self._last_fire: dict[str, float] = {}
        # Reglas activas cacheadas por símbolo.
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
        prev = self._last_price.get(symbol)
        self._last_price[symbol] = price
        if prev is None:
            return  # necesitamos dos precios para detectar un cruce

        for rule in self._rules_by_symbol.get(symbol, []):
            if self._crossed(rule, prev, price) and self._cooldown_ok(rule):
                await self._fire(rule, price)

    @staticmethod
    def _crossed(rule: dict, prev: float, current: float) -> bool:
        threshold = rule["threshold"]
        if rule["direction"] == "ABOVE":
            return prev < threshold <= current
        # BELOW
        return prev > threshold >= current

    def _cooldown_ok(self, rule: dict) -> bool:
        last = self._last_fire.get(rule["id"])
        if last is None:
            return True
        return (time.time() - last) >= rule["cooldownSeconds"]

    async def _fire(self, rule: dict, price: float) -> None:
        self._last_fire[rule["id"]] = time.time()
        arrow = "por encima de" if rule["direction"] == "ABOVE" else "por debajo de"
        message = (
            f"Alerta {rule['assetId'].upper()}: precio {price:g} "
            f"ha cruzado {arrow} {rule['threshold']:g}"
        )
        log.info("[ALERT] Disparada regla %s: %s", rule["id"], message)
        await telegram.send_message(message)
        await alerts_repo.mark_triggered(rule["id"])
