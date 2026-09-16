"""Contrato común de canales de notificación.

Permite añadir nuevos canales (Telegram, FCM, email...) sin tocar el código que
dispara las alertas. El motor de alertas usa el despachador (`dispatcher.py`),
no un canal concreto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Notifier(ABC):
    """Un canal de notificación."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre del canal (p. ej. 'telegram', 'fcm')."""

    @abstractmethod
    def is_configured(self) -> bool:
        """True si el canal tiene la configuración necesaria para enviar."""

    @abstractmethod
    async def send(self, text: str) -> bool:
        """Envía el mensaje. Devuelve True si se envió correctamente."""
