"""Repositorio de usuarios."""

from __future__ import annotations

import uuid

from sqlalchemy import text

from app.core.db import SessionLocal


def _row_to_dict(r) -> dict:
    return {
        "id": r.id,
        "email": r.email,
        "hashedPassword": r.hashed_password,
        "role": r.role,
        "isActive": r.is_active,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
    }


async def get_by_email(email: str) -> dict | None:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text("SELECT * FROM users WHERE email = :email"),
                {"email": email.lower()},
            )
        ).first()
        return _row_to_dict(row) if row else None


async def get_by_id(user_id: str) -> dict | None:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text("SELECT * FROM users WHERE id = :id"), {"id": user_id}
            )
        ).first()
        return _row_to_dict(row) if row else None


async def count_users() -> int:
    async with SessionLocal() as session:
        row = (await session.execute(text("SELECT COUNT(*) AS n FROM users"))).first()
        return int(row.n) if row else 0


async def create_user(email: str, hashed_password: str, role: str = "OWNER") -> dict:
    user_id = str(uuid.uuid4())
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO users (id, email, hashed_password, role, is_active)
                VALUES (:id, :email, :hashed_password, :role, TRUE)
                """
            ),
            {
                "id": user_id,
                "email": email.lower(),
                "hashed_password": hashed_password,
                "role": role,
            },
        )
        await session.commit()
    return {
        "id": user_id,
        "email": email.lower(),
        "role": role,
        "isActive": True,
    }
