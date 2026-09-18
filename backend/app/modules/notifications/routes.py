"""Endpoints de notificaciones por usuario (Telegram).

Flujo de vinculación (prueba de posesión del chat):
  1. El usuario autenticado pide un código:  POST /notifications/telegram/link
  2. Abre el bot y envía:  /start <código>
  3. Telegram llama al webhook (POST /notifications/telegram/webhook); se valida
     el código y se guarda el chat_id real de ESE chat.
  4. A partir de ahí, sus alertas se envían a su chat.

El bot es único del sistema (TELEGRAM_BOT_TOKEN). El watchdog operativo sigue
usando el chat global (TELEGRAM_CHAT_ID), ajeno a esto.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.auth.deps import CurrentUser, get_current_user
from app.modules.notifications import repository, telegram

log = get_logger("notifications.routes")

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/telegram")
async def telegram_status(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Estado de la vinculación de Telegram del usuario."""
    link = await repository.get_link(user.id)
    return {
        "botConfigured": bool(settings.telegram_bot_token),
        "linked": link is not None,
        "enabled": bool(link and link["enabled"]),
    }


@router.post("/telegram/link")
async def telegram_link_code(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Genera un código de un solo uso para vincular el chat del usuario.

    El usuario debe enviar `/start <code>` al bot para completar la vinculación.
    """
    if not settings.telegram_bot_token:
        return {"botConfigured": False}
    code, ttl = await repository.create_link_code(user.id)
    return {
        "botConfigured": True,
        "code": code,
        "expiresInSeconds": ttl,
        "instructions": f"Abre el bot de Telegram y envía: /start {code}",
    }


@router.post("/telegram/enabled")
async def telegram_set_enabled(
    body: dict, user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Activa o pausa el envío a Telegram sin desvincular el chat."""
    enabled = bool(body.get("enabled", True))
    affected = await repository.set_enabled(user.id, enabled)
    return {"updated": affected > 0, "enabled": enabled}


@router.delete("/telegram", status_code=204)
async def telegram_unlink(user: CurrentUser = Depends(get_current_user)) -> Response:
    """Desvincula el chat de Telegram del usuario."""
    # Response explícito: con `from __future__ import annotations`, un `-> None`
    # se estringiza y FastAPI intenta añadir cuerpo, incompatible con 204.
    await repository.delete_link(user.id)
    return Response(status_code=204)


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    """Recibe updates del bot. Vincula el chat cuando llega `/start <código>`.

    Seguridad: si TELEGRAM_WEBHOOK_SECRET está configurado, se exige que el
    header coincida (Telegram lo envía si se registró el webhook con secret).
    Responde siempre 200 para que Telegram no reintente en bucle.
    """
    secret = settings.telegram_webhook_secret
    if secret and x_telegram_bot_api_secret_token != secret:
        log.warning("[NOTIFY] Webhook de Telegram con secret inválido; ignorado")
        return {"ok": True}

    try:
        update = await request.json()
    except Exception:  # noqa: BLE001 - payload no-JSON: se ignora sin fallar
        return {"ok": True}

    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text_in = (message.get("text") or "").strip()

    if chat_id is None or not text_in.startswith("/start"):
        return {"ok": True}

    parts = text_in.split(maxsplit=1)
    code = parts[1].strip() if len(parts) > 1 else ""
    if not code:
        await telegram.send_to_chat(
            str(chat_id),
            "Para vincular tu cuenta, genera un código en la app y envía: /start <código>",
        )
        return {"ok": True}

    user_id = await repository.consume_link_code(code)
    if not user_id:
        await telegram.send_to_chat(
            str(chat_id),
            "Código inválido o caducado. Genera uno nuevo en la app e inténtalo otra vez.",
        )
        return {"ok": True}

    await repository.upsert_link(user_id, str(chat_id))
    await telegram.send_to_chat(
        str(chat_id),
        "✅ Chat vinculado. A partir de ahora recibirás aquí tus alertas de MarketTracker.",
    )
    log.info("[NOTIFY] Usuario %s vinculó su chat de Telegram", user_id)
    return {"ok": True}
