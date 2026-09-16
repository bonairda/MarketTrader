"""Configuración de la aplicación, cargada desde variables de entorno."""

from typing import Literal
from urllib.parse import quote, urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos
    postgres_user: str = "market"
    postgres_password: str = "market"
    postgres_db: str = "markettracker"
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url_override: str | None = Field(
        default=None, validation_alias="DATABASE_URL"
    )

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_url_override: str | None = Field(default=None, validation_alias="REDIS_URL")

    # API
    environment: Literal["local", "test", "staging", "production"] = "local"
    app_revision: str = "unknown"
    docs_enabled: bool = True
    log_level: str = "INFO"
    # Orígenes permitidos para CORS (separados por coma). "*" permite todos.
    cors_origins: str = "*"

    # Autenticación (JWT). CAMBIA jwt_secret en producción (variable de entorno).
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 días
    # Si es True, permite el registro abierto de nuevos usuarios (/auth/register).
    # En uso personal se puede dejar abierto; para cerrar el alta, ponlo a False.
    allow_registration: bool = True

    # Ingestión
    crypto_ws_url: str = "wss://stream.binance.com:9443/ws"
    default_crypto_symbols: str = "btcusdt,ethusdt"

    # Notificaciones (Telegram). Si no se configuran, las alertas se registran
    # en el log pero no se envían.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Watchdog de ingestión: si no llega ningún tick en este tiempo (segundos),
    # el worker avisa por Telegram de que la ingestión puede estar caída.
    ingestion_stale_seconds: int = 120
    # TTL del heartbeat que Docker/Coolify usa para comprobar el worker.
    worker_heartbeat_ttl_seconds: int = 30

    # Twelve Data (acciones y forex). Plan gratuito: sin WebSocket, se hace
    # polling REST. Si no hay clave, el proveedor no se activa.
    twelve_data_api_key: str = ""
    # Cada cuántos segundos se consulta el precio de acciones/forex (respetando
    # el límite del plan gratuito: ~8 req/min).
    twelve_data_poll_seconds: int = 60

    # Tipos de cambio a EUR (Banco Central Europeo). El feed diario publica el
    # cambio de referencia; se cachea en Redis para autorrellenar operaciones.
    ecb_fx_daily_url: str = (
        "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    )
    ecb_fx_history_url: str = (
        "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
    )
    ecb_fx_cache_ttl_seconds: int = 60 * 60 * 12  # 12 horas

    # Alpaca paper trading (SIN dinero real). Deshabilitado si no hay credenciales.
    # Usa SIEMPRE el host de paper por defecto; nunca la operativa real por accidente.
    alpaca_enabled: bool = False
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    @property
    def redis_url(self) -> str:
        if self.redis_url_override:
            return self.redis_url_override
        credentials = (
            f":{quote(self.redis_password, safe='')}@" if self.redis_password else ""
        )
        return f"redis://{credentials}{self.redis_host}:{self.redis_port}/0"

    @property
    def crypto_symbols(self) -> list[str]:
        return [s.strip() for s in self.default_crypto_symbols.split(",") if s.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def assert_safe_for_production(self) -> None:
        """Impide arrancar producción con secretos/orígenes de desarrollo."""
        if self.environment.lower() != "production":
            return
        if (
            self.jwt_secret == "change-me-in-production"
            or self.jwt_secret.startswith("REPLACE_")
            or len(self.jwt_secret) < 32
        ):
            raise RuntimeError("JWT_SECRET debe tener al menos 32 caracteres en producción")
        if not self.cors_origin_list:
            raise RuntimeError("CORS_ORIGINS no puede estar vacío en producción")
        if "*" in self.cors_origin_list:
            raise RuntimeError("CORS_ORIGINS no puede contener '*' en producción")
        if any(urlparse(origin).scheme != "https" for origin in self.cors_origin_list):
            raise RuntimeError("Todos los CORS_ORIGINS deben usar https en producción")
        weak = ("", "market", "change-me-in-production")
        if self.postgres_password in weak or self.postgres_password.startswith("REPLACE_"):
            raise RuntimeError("POSTGRES_PASSWORD no es seguro para producción")
        if self.redis_password in weak or self.redis_password.startswith("REPLACE_"):
            raise RuntimeError("REDIS_PASSWORD no es seguro para producción")


settings = Settings()
