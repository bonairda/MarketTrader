"""Configuración segura y URLs robustas para despliegue."""

import pytest

from app.core.config import Settings


def test_database_url_encodes_reserved_password_characters():
    settings = Settings(
        _env_file=None,
        postgres_user="market",
        postgres_password="p@ss:/#word",
        postgres_host="db",
        postgres_port=5432,
        postgres_db="tracker",
    )
    assert "p%40ss%3A%2F%23word" in settings.database_url
    assert settings.database_url.startswith("postgresql+asyncpg://market:")


def test_database_url_override_wins():
    custom = "postgresql+asyncpg://managed.example/tracker"
    settings = Settings(_env_file=None, DATABASE_URL=custom)
    assert settings.database_url == custom


def test_redis_password_is_url_encoded():
    settings = Settings(
        _env_file=None,
        redis_host="redis",
        redis_port=6379,
        redis_password="r@:/#",
    )
    assert settings.redis_url == "redis://:r%40%3A%2F%23@redis:6379/0"


def test_production_rejects_default_jwt():
    settings = Settings(
        _env_file=None,
        environment="production",
        cors_origins="https://market.example.com",
        postgres_password="p" * 32,
        redis_password="r" * 32,
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        settings.assert_safe_for_production()


def test_production_rejects_wildcard_cors():
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="x" * 64,
        cors_origins="*",
        postgres_password="p" * 32,
        redis_password="r" * 32,
    )
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        settings.assert_safe_for_production()


def test_production_accepts_strong_configuration():
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="x" * 64,
        cors_origins="https://market.example.com",
        postgres_password="p" * 32,
        redis_password="r" * 32,
    )
    settings.assert_safe_for_production()


def test_production_rejects_http_cors_origin():
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="x" * 64,
        cors_origins="http://market.example.com",
        postgres_password="p" * 32,
        redis_password="r" * 32,
    )
    with pytest.raises(RuntimeError, match="https"):
        settings.assert_safe_for_production()


def test_production_rejects_placeholder_passwords():
    settings = Settings(
        _env_file=None,
        environment="production",
        jwt_secret="x" * 64,
        cors_origins="https://market.example.com",
        postgres_password="REPLACE_WITH_A_LONG_RANDOM_SECRET",
        redis_password="r" * 32,
    )
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        settings.assert_safe_for_production()
