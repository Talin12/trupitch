"""Application settings loaded from environment variables via Pydantic."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "trupitch-api"
    # Host port 5433 (see docker-compose.yml); containers override via
    # DATABASE_URL pointing at postgres:5432 on the compose network.
    database_url: str = (
        "postgresql+asyncpg://trupitch:trupitch@localhost:5433/trupitch"
    )
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
