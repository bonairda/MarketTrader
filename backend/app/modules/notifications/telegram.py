"""Canal de notificación por Telegram.

Si no hay token/chat configurados, la notificación solo se registra en el log
(útil en desarrollo).
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.notifications.base import Notifier

log = get_logger("notifications.telegram")


class TelegramNotifier(Notifier):
    @property
    def name(self) -> str:
        return "telegram"

    def is_configured(self) -> bool:
        return bool(settings.telegram_bot_token and settings.telegram_chat_id)

    async def send(self, text: str) -> bool:
        if not self.is_configured():
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
