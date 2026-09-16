"""Despachador de notificaciones.

Dos modos de envío:
  - `notify(text)`               -> canales GLOBALES del sistema (watchdog, etc.).
  - `notify(text, user_id=...)`  -> notificación PERSONAL: al chat de Telegram
                                    vinculado por ese usuario (si lo tiene
                                    habilitado). Si no, cae en el log.

El resto del sistema (motor de alertas, watchdog) llama a `notify(...)` y no
depende de ningún canal concreto. Añadir un canal nuevo (p. ej. FCM) es
registrar un Notifier más para el caso global.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.modules.notifications import repository, telegram
from app.modules.notifications.base import Notifier
from app.modules.notifications.fcm import FcmNotifier
from app.modules.notifications.telegram import TelegramNotifier

log = get_logger("notifications.dispatcher")

# Canales globales del sistema. FCM está incluido pero hoy es un stub.
_NOTIFIERS: list[Notifier] = [TelegramNotifier(), FcmNotifier()]


async def notify(text: str, *, user_id: str | None = None) -> bool:
    """Envía `text`. Si `user_id` es None, usa los canales globales; si se indica,
    lo dirige al chat personal del usuario.

    Devuelve True si al menos un destino lo recibió correctamente.
    """
    if user_id is not None:
        return await _notify_user(user_id, text)
    return await _notify_global(text)


async def _notify_user(user_id: str, text: str) -> bool:
    chat_id = await repository.get_chat_id_if_enabled(user_id)
    if not chat_id:
        log.info(
            "[NOTIFY] Usuario %s sin Telegram vinculado/activo; mensaje solo en log: %s",
            user_id,
            text,
        )
        return False
    sent = await telegram.send_to_chat(chat_id, text)
    if not sent:
        log.info("[NOTIFY] No se pudo enviar al chat del usuario %s: %s", user_id, text)
    return sent


async def _notify_global(text: str) -> bool:
    sent_any = False
    for channel in _NOTIFIERS:
        if not channel.is_configured():
            continue
        if await channel.send(text):
            sent_any = True
    if not sent_any:
        log.info("[NOTIFY] Ningún canal global configurado; mensaje solo en log: %s", text)
    return sent_any
