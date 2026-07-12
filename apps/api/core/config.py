"""Application settings loaded from environment variables."""

import os


class Settings:
    app_name: str = "trupitch-api"
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://trupitch:trupitch@localhost:5432/trupitch"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


settings = Settings()
