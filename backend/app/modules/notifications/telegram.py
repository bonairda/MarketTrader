"""Canal de notificación por Telegram.

El bot es único del sistema (TELEGRAM_BOT_TOKEN). El destino puede ser:
  - el chat global (TELEGRAM_CHAT_ID): avisos operativos (watchdog).
  - el chat de un usuario concreto: sus alertas personales (ver dispatcher).

Si no hay token configurado, las notificaciones solo se registran en el log.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.notifications.base import Notifier

log = get_logger("notifications.telegram")


async def send_to_chat(chat_id: str, text: str) -> bool:
    """Envía `text` a un chat_id concreto usando el bot del sistema.

    Devuelve True si Telegram aceptó el mensaje. Requiere TELEGRAM_BOT_TOKEN.
    """
    if not settings.telegram_bot_token:
        log.info("[NOTIFY] (Telegram sin token) %s", text)
        return False
    if not chat_id:
        return False

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, json={"chat_id": chat_id, "text": text})
            if res.status_code != 200:
                log.warning("[NOTIFY] Telegram respondió %s: %s", res.status_code, res.text)
                return False
            return True
    except httpx.HTTPError as exc:
        log.error("[NOTIFY] Error enviando a Telegram: %s", exc)
        return False


class TelegramNotifier(Notifier):
    """Canal global (chat del sistema). Se usa para avisos operativos."""

    @property
    def name(self) -> str:
        return "telegram"

    def is_configured(self) -> bool:
        return bool(settings.telegram_bot_token and settings.telegram_chat_id)

    async def send(self, text: str) -> bool:
        if not self.is_configured():
            log.info("[NOTIFY] (Telegram global no configurado) %s", text)
            return False
        return await send_to_chat(settings.telegram_chat_id, text)
