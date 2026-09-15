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

    # Ingestión
    crypto_ws_url: str = "wss://stream.binance.com:9443/ws"
    default_crypto_symbols: str = "btcusdt,ethusdt"

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


settings = Settings()
