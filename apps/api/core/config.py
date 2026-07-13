"""Application settings loaded from environment variables via Pydantic."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root .env (shared across apps); a local apps/api/.env overrides it.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    app_name: str = "trupitch-api"
    # Host port 5433 (see docker-compose.yml); containers override via
    # DATABASE_URL pointing at postgres:5432 on the compose network.
    database_url: str = (
        "postgresql+asyncpg://trupitch:trupitch@localhost:5433/trupitch"
    )
    redis_url: str = "redis://localhost:6379/0"

    frontend_url: str = "http://localhost:5173"

    # Default organizer identity used when campaigns are created without an
    # explicit organizer (until the organizer OAuth flow exists).
    admin_email: str = "admin@trupitch.local"
    admin_name: str = "Admin User"

    # GitHub OAuth app credentials
    github_client_id: str = ""
    github_client_secret: str = ""

    # HS256 signing key for session JWTs. No default on purpose: a missing
    # JWT_SECRET must fail loudly, never silently mint forgeable tokens.
    jwt_secret: str

    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"), extra="ignore"
    )


settings = Settings()
