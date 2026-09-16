"""Panel de administración de usuarios. Requiere rol SUPERADMIN.

El superadmin (inicializado desde el entorno, ver core/bootstrap.py) puede
listar usuarios, crear nuevos, cambiar su rol, activarlos/desactivarlos y
borrarlos.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from app.modules.admin import service
from app.modules.auth.deps import CurrentUser, require_role

router = APIRouter(prefix="/admin", tags=["admin"])

# Todas las rutas exigen SUPERADMIN.
_superadmin = require_role("SUPERADMIN")


class CreateUserIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = Field(default="OWNER")


class RoleIn(BaseModel):
    role: str


class ActiveIn(BaseModel):
    isActive: bool


@router.get("/users")
async def list_users(admin: CurrentUser = Depends(_superadmin)) -> list[dict]:
    return await service.list_users()


@router.post("/users", status_code=201)
async def create_user(
    body: CreateUserIn, admin: CurrentUser = Depends(_superadmin)
) -> dict:
    return await service.create_user(str(body.email), body.password, body.role)


@router.put("/users/{user_id}/role")
async def set_role(
    user_id: str, body: RoleIn, admin: CurrentUser = Depends(_superadmin)
) -> dict:
    return await service.set_role(admin.id, user_id, body.role)


@router.put("/users/{user_id}/active")
async def set_active(
    user_id: str, body: ActiveIn, admin: CurrentUser = Depends(_superadmin)
) -> dict:
    return await service.set_active(admin.id, user_id, body.isActive)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str, admin: CurrentUser = Depends(_superadmin)
) -> None:
    await service.delete_user(admin.id, user_id)
