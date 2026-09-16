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


async def list_users() -> list[dict]:
    """Todos los usuarios (para el panel de administración)."""
    async with SessionLocal() as session:
        rows = await session.execute(
            text("SELECT * FROM users ORDER BY created_at ASC, email ASC")
        )
        return [_row_to_dict(r) for r in rows]


async def set_role(user_id: str, role: str) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            text("UPDATE users SET role = :role WHERE id = :id"),
            {"id": user_id, "role": role},
        )
        await session.commit()
        return result.rowcount or 0


async def set_active(user_id: str, is_active: bool) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            text("UPDATE users SET is_active = :active WHERE id = :id"),
            {"id": user_id, "active": is_active},
        )
        await session.commit()
        return result.rowcount or 0


async def delete_user(user_id: str) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            text("DELETE FROM users WHERE id = :id"), {"id": user_id}
        )
        await session.commit()
        return result.rowcount or 0


async def ensure_superadmin(email: str, hashed_password: str) -> dict:
    """Crea o actualiza el superadmin (bootstrap desde el entorno).

    Idempotente: si no existe lo crea con rol SUPERADMIN; si existe, le garantiza
    el rol SUPERADMIN, lo deja activo y actualiza la contraseña. Devuelve el
    usuario resultante.
    """
    email = email.lower()
    async with SessionLocal() as session:
        existing = (
            await session.execute(
                text("SELECT id FROM users WHERE email = :email"), {"email": email}
            )
        ).first()
        if existing:
            await session.execute(
                text(
                    """
                    UPDATE users
                    SET role = 'SUPERADMIN', is_active = TRUE, hashed_password = :hp
                    WHERE email = :email
                    """
                ),
                {"email": email, "hp": hashed_password},
            )
            user_id = existing.id
        else:
            user_id = str(uuid.uuid4())
            await session.execute(
                text(
                    """
                    INSERT INTO users (id, email, hashed_password, role, is_active)
                    VALUES (:id, :email, :hp, 'SUPERADMIN', TRUE)
                    """
                ),
                {"id": user_id, "email": email, "hp": hashed_password},
            )
        await session.commit()
    return {"id": user_id, "email": email, "role": "SUPERADMIN", "isActive": True}


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
