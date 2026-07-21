from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):

    app_name: str = "trupitch-api"
    database_url: str = (
        "postgresql+asyncpg://trupitch:trupitch@localhost:5433/trupitch"
    )
    redis_url: str = "redis://localhost:6379/0"

    frontend_url: str = "http://localhost:5173"

    admin_email: str = "admin@trupitch.local"
    admin_name: str = "Admin User"

    admin_username: str = "admin"
    admin_password: str = ""
    admin_session_secret: str = ""

    github_client_id: str = ""
    github_client_secret: str = ""

    jwt_secret: str

    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"), extra="ignore"
    )


settings = Settings()
