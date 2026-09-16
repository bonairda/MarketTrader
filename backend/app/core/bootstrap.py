"""Tareas de inicialización que se ejecutan al arrancar la API.

Hoy: garantizar el superadministrador definido por entorno. Es idempotente y
seguro de ejecutar en cada arranque (varias réplicas de la API pueden ejecutarlo
sin problema, el upsert converge al mismo estado).
"""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.modules.auth import repository as auth_repo

log = get_logger("bootstrap")


async def ensure_superadmin() -> None:
    """Crea o actualiza el superadmin si SUPERADMIN_EMAIL/PASSWORD están definidos."""
    if not settings.superadmin_enabled:
        return
    email = settings.superadmin_email.strip().lower()
    if "@" not in email:
        log.warning("[BOOTSTRAP] SUPERADMIN_EMAIL inválido; se omite el bootstrap")
        return
    try:
        await auth_repo.ensure_superadmin(email, hash_password(settings.superadmin_password))
        log.info("[BOOTSTRAP] Superadmin garantizado: %s", email)
    except Exception as exc:  # noqa: BLE001 - no debe impedir el arranque de la API
        log.error("[BOOTSTRAP] No se pudo garantizar el superadmin: %s", exc)
