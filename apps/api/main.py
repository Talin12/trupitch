"""TruPitch API entrypoint."""

from fastapi import FastAPI

from core.config import settings

app = FastAPI(
    title="TruPitch API",
    description="Automated hackathon submission filtering and judging platform.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe for load balancers and orchestrators."""
    return {"status": "ok", "service": settings.app_name}
