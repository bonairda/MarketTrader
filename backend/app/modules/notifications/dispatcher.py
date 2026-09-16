"""Despachador de notificaciones.

Envía un mensaje por todos los canales configurados. El resto del sistema (motor
de alertas, watchdog) llama a `notify(...)` y no depende de ningún canal concreto.
Añadir un canal nuevo (p. ej. FCM cuando esté listo) es registrar un Notifier más.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.modules.notifications.base import Notifier
from app.modules.notifications.fcm import FcmNotifier
from app.modules.notifications.telegram import TelegramNotifier

log = get_logger("notifications.dispatcher")

# Canales disponibles. FCM está incluido pero hoy no está configurado (stub).
_NOTIFIERS: list[Notifier] = [TelegramNotifier(), FcmNotifier()]


async def notify(text: str) -> bool:
    """Envía el mensaje por todos los canales configurados.

    Devuelve True si al menos un canal lo envió correctamente.
    """
    sent_any = False
    for channel in _NOTIFIERS:
        if not channel.is_configured():
            continue
        if await channel.send(text):
            sent_any = True
    if not sent_any:
        log.info("[NOTIFY] Ningún canal configurado; mensaje solo en log: %s", text)
    return sent_any
