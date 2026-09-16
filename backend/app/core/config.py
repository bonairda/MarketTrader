"""Configuración de la aplicación, cargada desde variables de entorno."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos
    postgres_user: str = "market"
    postgres_password: str = "market"
    postgres_db: str = "markettracker"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379

    # API
    log_level: str = "INFO"
    # Orígenes permitidos para CORS (separados por coma). "*" permite todos.
    cors_origins: str = "*"

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

    # Twelve Data (acciones y forex). Plan gratuito: sin WebSocket, se hace
    # polling REST. Si no hay clave, el proveedor no se activa.
    twelve_data_api_key: str = ""
    # Cada cuántos segundos se consulta el precio de acciones/forex (respetando
    # el límite del plan gratuito: ~8 req/min).
    twelve_data_poll_seconds: int = 60

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def crypto_symbols(self) -> list[str]:
        return [s.strip() for s in self.default_crypto_symbols.split(",") if s.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
