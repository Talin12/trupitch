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

setup_admin(app)

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
    return {"status": "ok", "service": settings.app_name}
