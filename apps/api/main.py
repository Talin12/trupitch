"""TruPitch API entrypoint.

Run locally with: `uvicorn main:app --reload` (from apps/api/, inside
the shared .venv). This module wires together the FastAPI app instance,
CORS policy, and every router — it holds no business logic of its own
beyond the /health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin import setup_admin
from core.config import settings
from routers import auth, campaigns, hacker, submissions

app = FastAPI(
    title="TruPitch API",
    description="Automated hackathon submission filtering and judging platform.",
    version="0.1.0",
)

# Internal staff CRUD panel at /admin (SQLAdmin). Introspects the ORM
# models, so migrations surface here automatically. Gated by ADMIN_PASSWORD
# — see apps/api/admin.py.
setup_admin(app)

# Only the configured frontend origin may call this API from a browser.
# allow_credentials=True is required because the SPA sends the session
# JWT as an Authorization header on cross-origin requests (localhost:5173
# -> localhost:8000 counts as cross-origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every router is mounted under /api, so e.g. campaigns.router's
# `@router.get("/{campaign_id}")` becomes GET /api/campaigns/{campaign_id}.
app.include_router(auth.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(hacker.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe for load balancers and orchestrators."""
    return {"status": "ok", "service": settings.app_name}
