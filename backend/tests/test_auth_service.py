"""Tests del servicio de autenticación (registro/login) con repositorio simulado.

No tocan la base de datos: se sustituye `repository` por un almacén en memoria.
"""

import uuid

import pytest

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.modules.auth import service as service_module


class _FakeUserRepo:
    """Repositorio de usuarios en memoria, con la misma interfaz que el real."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}

    async def count_users(self) -> int:
        return len(self.users)

    async def get_by_email(self, email: str) -> dict | None:
        for u in self.users.values():
            if u["email"] == email.lower():
                return u
        return None

    async def get_by_id(self, user_id: str) -> dict | None:
        return self.users.get(user_id)

    async def create_user(self, email: str, hashed_password: str, role: str = "OWNER") -> dict:
        user_id = str(uuid.uuid4())
        self.users[user_id] = {
            "id": user_id,
            "email": email.lower(),
            "hashedPassword": hashed_password,
            "role": role,
            "isActive": True,
        }
        return {"id": user_id, "email": email.lower(), "role": role, "isActive": True}


@pytest.fixture
def repo(monkeypatch):
    fake = _FakeUserRepo()
    monkeypatch.setattr(service_module, "repository", fake)
    return fake


async def test_register_creates_user_and_returns_token(repo):
    result = await service_module.register("nuevo@example.com", "password123")
    assert result["user"]["email"] == "nuevo@example.com"
    assert result["user"]["role"] == "OWNER"
    payload = decode_access_token(result["token"])
    assert payload is not None
    assert payload["sub"] == result["user"]["id"]


async def test_register_normalizes_email(repo):
    result = await service_module.register("  MixedCase@Example.COM ", "password123")
    assert result["user"]["email"] == "mixedcase@example.com"


async def test_register_rejects_short_password(repo):
    with pytest.raises(AppError) as exc:
        await service_module.register("a@b.com", "short")
    assert exc.value.status_code == 422
    assert exc.value.code == "WEAK_PASSWORD"


async def test_register_rejects_invalid_email(repo):
    with pytest.raises(AppError) as exc:
        await service_module.register("no-es-email", "password123")
    assert exc.value.code == "INVALID_EMAIL"


async def test_register_rejects_duplicate_email(repo):
    await service_module.register("dup@example.com", "password123")
    with pytest.raises(AppError) as exc:
        await service_module.register("dup@example.com", "otracosa123")
    assert exc.value.status_code == 409
    assert exc.value.code == "EMAIL_TAKEN"


async def test_register_closed_after_first_user(repo, monkeypatch):
    # Con el registro cerrado, el primer usuario (bootstrap) SÍ se permite...
    monkeypatch.setattr(service_module.settings, "allow_registration", False)
    await service_module.register("owner@example.com", "password123")
    # ...pero el segundo NO.
    with pytest.raises(AppError) as exc:
        await service_module.register("otro@example.com", "password123")
    assert exc.value.status_code == 403
    assert exc.value.code == "REGISTRATION_CLOSED"


async def test_login_succeeds_with_correct_credentials(repo):
    await service_module.register("login@example.com", "password123")
    result = await service_module.login("login@example.com", "password123")
    payload = decode_access_token(result["token"])
    assert payload is not None
    assert result["user"]["email"] == "login@example.com"


async def test_login_wrong_password_is_401(repo):
    await service_module.register("login@example.com", "password123")
    with pytest.raises(AppError) as exc:
        await service_module.login("login@example.com", "incorrecta")
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_CREDENTIALS"


async def test_login_unknown_email_is_401(repo):
    with pytest.raises(AppError) as exc:
        await service_module.login("noexiste@example.com", "password123")
    # Mismo error que contraseña incorrecta (no revela si el email existe).
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_CREDENTIALS"


async def test_login_disabled_user_is_403(repo):
    await service_module.register("dis@example.com", "password123")
    # Desactivar el usuario directamente en el almacén.
    for u in repo.users.values():
        u["isActive"] = False
    with pytest.raises(AppError) as exc:
        await service_module.login("dis@example.com", "password123")
    assert exc.value.status_code == 403
    assert exc.value.code == "USER_DISABLED"


async def test_login_does_not_leak_password_hash(repo):
    await service_module.register("hash@example.com", "password123")
    result = await service_module.login("hash@example.com", "password123")
    assert "hashedPassword" not in result["user"]
    assert "hashed_password" not in result["user"]
