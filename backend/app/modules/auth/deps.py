"""Dependencias de autenticación para FastAPI.

`get_current_user` extrae el usuario del token Bearer y lo inyecta en las rutas.
Todas las rutas de datos personales dependen de ella, de modo que el `user_id`
queda disponible para filtrar SIEMPRE por usuario.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.modules.auth import repository

# auto_error=False para poder devolver nuestro propio error 401 consistente.
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    role: str


class AuthError(AppError):
    def __init__(self, message: str = "No autenticado", *, code: str = "UNAUTHORIZED"):
        super().__init__(message, code=code, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "No autorizado", *, code: str = "FORBIDDEN"):
        super().__init__(message, code=code, status_code=403)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise AuthError("Falta el token de acceso")
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise AuthError("Token inválido o caducado")

    user = await repository.get_by_id(payload["sub"])
    if not user:
        raise AuthError("El usuario del token ya no existe")
    if not user["isActive"]:
        raise ForbiddenError("Usuario desactivado")
    return CurrentUser(id=user["id"], email=user["email"], role=user["role"])


def require_role(*roles: str):
    """Devuelve una dependencia que exige que el usuario tenga uno de los roles."""

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError(f"Requiere rol {' o '.join(roles)}")
        return user

    return _checker
