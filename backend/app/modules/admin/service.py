"""Servicio de administración de usuarios (solo SUPERADMIN).

Reutiliza el repositorio de auth. Aplica las reglas de negocio y salvaguardas:
  - Roles válidos: SUPERADMIN, OWNER, VIEWER.
  - Un superadmin no puede degradarse, desactivarse ni borrarse a sí mismo
    (evita quedarse sin ningún superadmin por error).
"""

from __future__ import annotations

from app.core.errors import AppError, NotFoundError
from app.core.security import hash_password
from app.modules.auth import repository as auth_repo

VALID_ROLES = ("SUPERADMIN", "OWNER", "VIEWER")


def _public(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "isActive": user.get("isActive", True),
        "createdAt": user.get("createdAt"),
    }


def _validate_role(role: str) -> str:
    role = (role or "").strip().upper()
    if role not in VALID_ROLES:
        raise AppError(
            f"Rol no válido. Debe ser uno de: {', '.join(VALID_ROLES)}",
            code="INVALID_ROLE",
            status_code=422,
        )
    return role


async def list_users() -> list[dict]:
    return [_public(u) for u in await auth_repo.list_users()]


async def create_user(email: str, password: str, role: str) -> dict:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise AppError("Email no válido", code="INVALID_EMAIL", status_code=422)
    if len(password or "") < 8:
        raise AppError(
            "La contraseña debe tener al menos 8 caracteres",
            code="WEAK_PASSWORD",
            status_code=422,
        )
    role = _validate_role(role)
    if await auth_repo.get_by_email(email):
        raise AppError("El email ya está registrado", code="EMAIL_TAKEN", status_code=409)
    user = await auth_repo.create_user(email, hash_password(password), role=role)
    return _public({**user, "isActive": True})


async def set_role(actor_id: str, user_id: str, role: str) -> dict:
    role = _validate_role(role)
    target = await auth_repo.get_by_id(user_id)
    if not target:
        raise NotFoundError("Usuario no encontrado")
    if actor_id == user_id and role != "SUPERADMIN":
        raise AppError(
            "No puedes quitarte a ti mismo el rol de superadmin",
            code="SELF_DEMOTE_FORBIDDEN",
            status_code=409,
        )
    await auth_repo.set_role(user_id, role)
    return _public({**target, "role": role})


async def set_active(actor_id: str, user_id: str, is_active: bool) -> dict:
    target = await auth_repo.get_by_id(user_id)
    if not target:
        raise NotFoundError("Usuario no encontrado")
    if actor_id == user_id and not is_active:
        raise AppError(
            "No puedes desactivar tu propia cuenta de superadmin",
            code="SELF_DISABLE_FORBIDDEN",
            status_code=409,
        )
    await auth_repo.set_active(user_id, is_active)
    return _public({**target, "isActive": is_active})


async def delete_user(actor_id: str, user_id: str) -> None:
    if actor_id == user_id:
        raise AppError(
            "No puedes borrar tu propia cuenta de superadmin",
            code="SELF_DELETE_FORBIDDEN",
            status_code=409,
        )
    target = await auth_repo.get_by_id(user_id)
    if not target:
        raise NotFoundError("Usuario no encontrado")
    await auth_repo.delete_user(user_id)
