"""TruPitch API entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import auth, campaigns, hacker, submissions

app = FastAPI(
    title="TruPitch API",
    description="Automated hackathon submission filtering and judging platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(hacker.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe for load balancers and orchestrators."""
    return {"status": "ok", "service": settings.app_name}
