"""Canal de notificación por Firebase Cloud Messaging (push móvil).

PENDIENTE (F1+): implementación real. FCM requiere:
  - Un proyecto Firebase y credenciales de cuenta de servicio.
  - Registrar los tokens de dispositivo (la app ya tiene la tabla `Device`).
  - Enviar a la HTTP v1 API de FCM con esos tokens.

De momento es un stub: nunca está "configurado", así que el despachador lo
ignora. Al implementarlo, basta con completar `is_configured` y `send`; el resto
del sistema (motor de alertas) no cambia.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.modules.notifications.base import Notifier

log = get_logger("notifications.fcm")


class FcmNotifier(Notifier):
    @property
    def name(self) -> str:
        return "fcm"

    def is_configured(self) -> bool:
        # TODO(F1+): devolver True cuando existan credenciales de Firebase.
        return False

    async def send(self, text: str) -> bool:
        log.debug("[NOTIFY] FCM aún no implementado; mensaje omitido")
        return False
