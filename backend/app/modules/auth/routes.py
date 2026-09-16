"""Endpoints de autenticación."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from app.modules.auth import service
from app.modules.auth.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
async def register(body: RegisterIn) -> dict:
    return await service.register(str(body.email), body.password)


@router.post("/login")
async def login(body: LoginIn) -> dict:
    return await service.login(str(body.email), body.password)


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role}
