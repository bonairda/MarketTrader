"""Tests de las utilidades de seguridad: hash de contraseñas y JWT."""

from datetime import UTC, datetime, timedelta

import jwt

from app.core import security
from app.core.config import settings


def test_hash_password_is_not_plaintext_and_verifies():
    hashed = security.hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert security.verify_password("s3cret-password", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = security.hash_password("correcta")
    assert security.verify_password("incorrecta", hashed) is False


def test_hash_password_uses_random_salt():
    # Dos hashes de la misma contraseña deben diferir (sal aleatoria) y ambos verificar.
    h1 = security.hash_password("misma")
    h2 = security.hash_password("misma")
    assert h1 != h2
    assert security.verify_password("misma", h1)
    assert security.verify_password("misma", h2)


def test_verify_password_handles_garbage_hash():
    # Un hash inválido no debe lanzar excepción, solo devolver False.
    assert security.verify_password("x", "no-es-un-hash-bcrypt") is False


def test_jwt_round_trip_carries_subject_and_role():
    token = security.create_access_token("user-123", role="OWNER")
    payload = security.decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "OWNER"


def test_decode_rejects_tampered_token():
    token = security.create_access_token("user-123", role="OWNER")
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    assert security.decode_access_token(tampered) is None


def test_decode_rejects_wrong_secret():
    # Token firmado con otro secreto -> inválido.
    other = jwt.encode(
        {"sub": "x", "role": "OWNER"}, "otro-secreto", algorithm=settings.jwt_algorithm
    )
    assert security.decode_access_token(other) is None


def test_decode_rejects_expired_token():
    # Token ya caducado (exp en el pasado).
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "x",
            "role": "OWNER",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert security.decode_access_token(expired) is None
