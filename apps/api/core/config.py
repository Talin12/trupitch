"""Application settings loaded from environment variables via Pydantic."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root .env (shared across apps); a local apps/api/.env overrides it.
# parents[3] because this file lives at apps/api/core/config.py, so we
# need to climb: core -> api -> apps -> <repo root>.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Every field below can be overridden by an environment variable of
    the same name (upper-cased), e.g. DATABASE_URL, JWT_SECRET, etc.
    Pydantic-settings reads them automatically — nothing in the rest of
    the codebase should read os.environ directly for these values.
    """

    app_name: str = "trupitch-api"
    # Host port 5433 (see docker-compose.yml); containers override via
    # DATABASE_URL pointing at postgres:5432 on the compose network.
    database_url: str = (
        "postgresql+asyncpg://trupitch:trupitch@localhost:5433/trupitch"
    )
    redis_url: str = "redis://localhost:6379/0"

    # Base URL of the React SPA. Used to build the CORS allow-list and the
    # redirect target after a successful GitHub OAuth login.
    frontend_url: str = "http://localhost:5173"

    # Default organizer identity used when campaigns are created without an
    # explicit organizer (until the organizer OAuth flow exists).
    admin_email: str = "admin@trupitch.local"
    admin_name: str = "Admin User"

    # GitHub OAuth app credentials (create at github.com/settings/developers).
    # Used by routers/auth.py to run the login/callback exchange.
    github_client_id: str = ""
    github_client_secret: str = ""

    # HS256 signing key for session JWTs. No default on purpose: a missing
    # JWT_SECRET must fail loudly, never silently mint forgeable tokens.
    jwt_secret: str

    # Tell pydantic-settings where to look for a .env file, and to ignore
    # any extra keys in that file instead of raising a validation error.
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"), extra="ignore"
    )


# Instantiated once at import time; every module does
# `from core.config import settings` and reads attributes off this shared
# singleton rather than constructing its own Settings().
settings = Settings()
