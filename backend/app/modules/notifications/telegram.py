"""Envío de notificaciones por Telegram.

Si no hay token/chat configurados, la notificación solo se registra en el log
(útil en desarrollo). FCM (push móvil) se añadirá más adelante; requiere un
proyecto Firebase y credenciales de servicio.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("notifications.telegram")


async def send_message(text: str) -> bool:
    """Envía un mensaje al chat de Telegram configurado. Devuelve True si se envió."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        log.info("[NOTIFY] (Telegram no configurado) %s", text)
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                url,
                json={"chat_id": settings.telegram_chat_id, "text": text},
            )
            if res.status_code != 200:
                log.warning("[NOTIFY] Telegram respondió %s: %s", res.status_code, res.text)
                return False
            return True
    except httpx.HTTPError as exc:
        log.error("[NOTIFY] Error enviando a Telegram: %s", exc)
        return False
