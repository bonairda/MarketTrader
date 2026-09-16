"""Servicio de autenticación: registro y login."""

from __future__ import annotations

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth import repository


async def register(email: str, password: str) -> dict:
    """Registra un usuario nuevo y devuelve un token de acceso.

    El primer usuario que se registra es OWNER. Si el registro abierto está
    deshabilitado (`allow_registration=False`), solo se permite crear el primer
    usuario (bootstrap); a partir de ahí, el alta queda cerrada.
    """
    email = email.strip().lower()
    if not email or "@" not in email:
        raise AppError("Email no válido", code="INVALID_EMAIL", status_code=422)
    if len(password) < 8:
        raise AppError(
            "La contraseña debe tener al menos 8 caracteres",
            code="WEAK_PASSWORD",
            status_code=422,
        )

    existing_count = await repository.count_users()
    if existing_count > 0 and not settings.allow_registration:
        raise AppError("El registro está deshabilitado", code="REGISTRATION_CLOSED", status_code=403)

    if await repository.get_by_email(email):
        raise AppError("El email ya está registrado", code="EMAIL_TAKEN", status_code=409)

    # El primer usuario del sistema es OWNER; el resto también OWNER por ahora
    # (roles se afinan más adelante). Se deja explícito para claridad.
    role = "OWNER"
    user = await repository.create_user(email, hash_password(password), role=role)
    token = create_access_token(user["id"], role=user["role"])
    return {"token": token, "user": _public(user)}


async def login(email: str, password: str) -> dict:
    """Valida credenciales y devuelve un token. Mensaje genérico si fallan."""
    email = email.strip().lower()
    user = await repository.get_by_email(email)
    # Mismo error tanto si el email no existe como si la contraseña falla,
    # para no revelar qué emails están registrados.
    if not user or not verify_password(password, user["hashedPassword"]):
        raise AppError("Credenciales incorrectas", code="INVALID_CREDENTIALS", status_code=401)
    if not user["isActive"]:
        raise AppError("Usuario desactivado", code="USER_DISABLED", status_code=403)
    token = create_access_token(user["id"], role=user["role"])
    return {"token": token, "user": _public(user)}


def _public(user: dict) -> dict:
    """Vista pública del usuario (sin el hash de la contraseña)."""
    return {"id": user["id"], "email": user["email"], "role": user["role"]}
