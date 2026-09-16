"""Tests del despachador de notificaciones."""

from app.modules.notifications import dispatcher as dispatcher_module
from app.modules.notifications.base import Notifier


class _FakeNotifier(Notifier):
    def __init__(self, name: str, configured: bool, ok: bool = True) -> None:
        self._name = name
        self._configured = configured
        self._ok = ok
        self.sent: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return self._configured

    async def send(self, text: str) -> bool:
        self.sent.append(text)
        return self._ok


async def test_notify_uses_only_configured_channels(monkeypatch):
    configured = _FakeNotifier("a", configured=True)
    not_configured = _FakeNotifier("b", configured=False)
    monkeypatch.setattr(dispatcher_module, "_NOTIFIERS", [configured, not_configured])

    result = await dispatcher_module.notify("hola")

    assert result is True
    assert configured.sent == ["hola"]
    assert not_configured.sent == []  # no se le pide enviar si no está configurado


async def test_notify_returns_false_when_no_channel_sends(monkeypatch):
    none = _FakeNotifier("a", configured=False)
    monkeypatch.setattr(dispatcher_module, "_NOTIFIERS", [none])

    result = await dispatcher_module.notify("hola")

    assert result is False


async def test_notify_true_if_any_channel_succeeds(monkeypatch):
    fails = _FakeNotifier("a", configured=True, ok=False)
    works = _FakeNotifier("b", configured=True, ok=True)
    monkeypatch.setattr(dispatcher_module, "_NOTIFIERS", [fails, works])

    result = await dispatcher_module.notify("hola")

    assert result is True
    assert fails.sent == ["hola"]
    assert works.sent == ["hola"]
