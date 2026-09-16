"""Repositorio del vínculo de Telegram por usuario.

Persiste el chat_id de cada usuario (tabla user_telegram_links) y gestiona el
código de vinculación de un solo uso en Redis. El flujo de vinculación prueba la
posesión del chat: el usuario pide un código en la app y lo envía al bot con
`/start <código>`; el webhook valida el código y guarda el chat_id real.
"""

from __future__ import annotations

import secrets

from sqlalchemy import text

from app.core.db import SessionLocal
from app.core.redis_client import get_redis

# Código de vinculación: clave code -> user_id, y su inverso para poder revocar
# un código pendiente si el usuario pide uno nuevo.
_LINK_CODE_KEY = "notify:tg:linkcode:"        # + code  -> user_id
_LINK_PENDING_KEY = "notify:tg:linkpending:"  # + user_id -> code
_LINK_CODE_TTL_SECONDS = 600  # 10 minutos


def _row_to_dict(r) -> dict:
    return {
        "userId": r.user_id,
        "chatId": r.chat_id,
        "enabled": r.enabled,
        "createdAt": r.created_at.isoformat() if r.created_at else None,
        "updatedAt": r.updated_at.isoformat() if r.updated_at else None,
    }


# ----------------------------------------------------------------------
# Vínculo persistente (Postgres)
# ----------------------------------------------------------------------
async def get_link(user_id: str) -> dict | None:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                text("SELECT * FROM user_telegram_links WHERE user_id = :uid"),
                {"uid": user_id},
            )
        ).first()
        return _row_to_dict(row) if row else None


async def upsert_link(user_id: str, chat_id: str) -> dict:
    """Crea o actualiza el chat vinculado del usuario y lo deja habilitado."""
    async with SessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO user_telegram_links (user_id, chat_id, enabled, updated_at)
                VALUES (:uid, :chat_id, TRUE, now())
                ON CONFLICT (user_id)
                DO UPDATE SET chat_id = EXCLUDED.chat_id,
                              enabled = TRUE,
                              updated_at = now()
                """
            ),
            {"uid": user_id, "chat_id": chat_id},
        )
        await session.commit()
    return {"userId": user_id, "chatId": chat_id, "enabled": True}


async def set_enabled(user_id: str, enabled: bool) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            text(
                "UPDATE user_telegram_links SET enabled = :enabled, updated_at = now() "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id, "enabled": enabled},
        )
        await session.commit()
        return result.rowcount or 0


async def delete_link(user_id: str) -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            text("DELETE FROM user_telegram_links WHERE user_id = :uid"),
            {"uid": user_id},
        )
        await session.commit()
        return result.rowcount or 0


async def get_chat_id_if_enabled(user_id: str) -> str | None:
    """chat_id del usuario si tiene vínculo habilitado; None en caso contrario."""
    link = await get_link(user_id)
    if link and link["enabled"]:
        return link["chatId"]
    return None


# ----------------------------------------------------------------------
# Código de vinculación de un solo uso (Redis)
# ----------------------------------------------------------------------
async def create_link_code(user_id: str) -> tuple[str, int]:
    """Genera un código para el usuario e invalida el anterior si existía.

    Devuelve (código, ttl_segundos).
    """
    redis = get_redis()
    # Revoca un código pendiente previo del mismo usuario.
    previous = await redis.get(f"{_LINK_PENDING_KEY}{user_id}")
    if previous:
        await redis.delete(f"{_LINK_CODE_KEY}{previous}")

    # Código corto, legible y suficientemente aleatorio para un TTL de 10 min.
    code = secrets.token_hex(4).upper()  # 8 caracteres hex
    await redis.set(f"{_LINK_CODE_KEY}{code}", user_id, ex=_LINK_CODE_TTL_SECONDS)
    await redis.set(f"{_LINK_PENDING_KEY}{user_id}", code, ex=_LINK_CODE_TTL_SECONDS)
    return code, _LINK_CODE_TTL_SECONDS


async def consume_link_code(code: str) -> str | None:
    """Valida y consume un código (un solo uso). Devuelve el user_id o None."""
    redis = get_redis()
    key = f"{_LINK_CODE_KEY}{code.strip().upper()}"
    user_id = await redis.get(key)
    if not user_id:
        return None
    await redis.delete(key)
    await redis.delete(f"{_LINK_PENDING_KEY}{user_id}")
    return user_id
