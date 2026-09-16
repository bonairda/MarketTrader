"""Valoración de posiciones de cartera (lógica pura).

Dado el estado de una posición (cantidad, precio medio) y su precio actual,
calcula valor de mercado, coste, P&L absoluto y porcentual.
"""

from __future__ import annotations


def value_position(quantity: float, average_price: float, current_price: float | None) -> dict:
    cost = quantity * average_price
    if current_price is None:
        return {
            "marketValue": None,
            "cost": cost,
            "pnl": None,
            "pnlPercent": None,
        }
    market_value = quantity * current_price
    pnl = market_value - cost
    pnl_percent = (pnl / cost * 100) if cost != 0 else None
    return {
        "marketValue": market_value,
        "cost": cost,
        "pnl": pnl,
        "pnlPercent": pnl_percent,
    }


def summarize(valued_positions: list[dict]) -> dict:
    """Totales de la cartera a partir de posiciones ya valoradas."""
    total_cost = sum(p["cost"] for p in valued_positions)
    # Solo suma valor/pnl de las posiciones con precio disponible.
    priced = [p for p in valued_positions if p["marketValue"] is not None]
    total_value = sum(p["marketValue"] for p in priced)
    total_pnl = sum(p["pnl"] for p in priced)
    # El porcentaje usa solo el coste valorado; dividir P&L parcial por el coste
    # de posiciones sin precio sesgaría el resultado a la baja.
    priced_cost = sum(p["cost"] for p in priced)
    total_pnl_percent = (total_pnl / priced_cost * 100) if priced_cost != 0 else None
    return {
        "totalCost": total_cost,
        "totalValue": total_value,
        "totalPnl": total_pnl,
        "totalPnlPercent": total_pnl_percent,
        "positions": len(valued_positions),
    }
