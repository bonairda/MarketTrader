"""Tests de la dependencia get_current_user y require_role."""

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.errors import AppError
from app.core.security import create_access_token
from app.modules.auth import deps as deps_module
from app.modules.auth.deps import CurrentUser, get_current_user, require_role


class _FakeUserRepo:
    def __init__(self, users: dict[str, dict]) -> None:
        self.users = users

    async def get_by_id(self, user_id: str) -> dict | None:
        return self.users.get(user_id)


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def active_user(monkeypatch):
    user = {"id": "u1", "email": "a@b.com", "role": "OWNER", "isActive": True}
    monkeypatch.setattr(deps_module, "repository", _FakeUserRepo({"u1": user}))
    return user


async def test_get_current_user_valid_token(active_user):
    token = create_access_token("u1", role="OWNER")
    user = await get_current_user(_creds(token))
    assert isinstance(user, CurrentUser)
    assert user.id == "u1"
    assert user.role == "OWNER"


async def test_get_current_user_missing_credentials(active_user):
    with pytest.raises(AppError) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401


async def test_get_current_user_invalid_token(active_user):
    with pytest.raises(AppError) as exc:
        await get_current_user(_creds("no-es-un-jwt"))
    assert exc.value.status_code == 401


async def test_get_current_user_unknown_user(monkeypatch):
    # Token válido pero el usuario ya no existe en la BD.
    monkeypatch.setattr(deps_module, "repository", _FakeUserRepo({}))
    token = create_access_token("desaparecido", role="OWNER")
    with pytest.raises(AppError) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 401


async def test_get_current_user_disabled_user(monkeypatch):
    user = {"id": "u2", "email": "x@y.com", "role": "OWNER", "isActive": False}
    monkeypatch.setattr(deps_module, "repository", _FakeUserRepo({"u2": user}))
    token = create_access_token("u2", role="OWNER")
    with pytest.raises(AppError) as exc:
        await get_current_user(_creds(token))
    assert exc.value.status_code == 403


async def test_require_role_allows_matching_role():
    checker = require_role("OWNER")
    user = CurrentUser(id="u1", email="a@b.com", role="OWNER")
    result = await checker(user)
    assert result is user


async def test_require_role_blocks_other_role():
    checker = require_role("OWNER")
    viewer = CurrentUser(id="u3", email="v@b.com", role="VIEWER")
    with pytest.raises(AppError) as exc:
        await checker(viewer)
    assert exc.value.status_code == 403
