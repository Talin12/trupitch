"""GitHub OAuth flow for hacker identity verification."""

import logging
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import create_access_token
from models import Hacker

STATE_TTL = timedelta(minutes=10)


def _issue_state(next_path: str) -> str:
    """Short-lived signed token proving the OAuth flow started with us.

    Carries the SPA path to return to after login.
    """
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "purpose": "oauth_state",
            "next": next_path,
            "iat": now,
            "exp": now + STATE_TTL,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def _check_state(state: str | None) -> dict:
    try:
        payload = jwt.decode(
            state or "", settings.jwt_secret, algorithms=["HS256"]
        )
        if payload.get("purpose") != "oauth_state":
            raise jwt.InvalidTokenError("wrong purpose")
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state; restart the login flow",
        )


def _safe_next(next_path: str) -> str:
    """Only same-origin SPA paths; anything else falls back to home."""
    if next_path.startswith("/") and not next_path.startswith("//"):
        return next_path
    return "/"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/github/login")
async def github_login(next: str = "/") -> RedirectResponse:
    """Send the hacker to GitHub's consent screen.

    `next` is the SPA path to return to after authentication.
    """
    if not settings.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_CLIENT_ID is not configured",
        )
    return RedirectResponse(
        f"{GITHUB_AUTHORIZE_URL}"
        f"?client_id={settings.github_client_id}&scope=repo"
        f"&state={_issue_state(_safe_next(next))}"
    )


@router.get("/github/callback")
async def github_callback(
    code: str, state: str | None = None, db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    """Exchange the OAuth code, upsert the hacker, hand a JWT to the SPA."""
    state_payload = _check_state(state)
    next_path = _safe_next(state_payload.get("next", "/"))
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            token_resp = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub token exchange failed: {exc}",
            )

        access_token = (
            token_resp.json().get("access_token")
            if token_resp.status_code == 200
            else None
        )
        if not access_token:
            logger.warning("OAuth exchange rejected: %s", token_resp.text[:200])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub rejected the OAuth code",
            )

        try:
            user_resp = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub user lookup failed: {exc}",
            )

    if user_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch GitHub user profile",
        )
    user = user_resp.json()
    github_id = str(user["id"])
    username = user["login"]

    hacker = (
        await db.execute(select(Hacker).where(Hacker.github_id == github_id))
    ).scalar_one_or_none()
    if hacker is None:
        hacker = Hacker(
            github_id=github_id, username=username, github_token=access_token
        )
        db.add(hacker)
    else:
        hacker.username = username
        hacker.github_token = access_token
    await db.commit()
    await db.refresh(hacker)

    jwt_token = create_access_token(hacker.id)
    return RedirectResponse(f"{settings.frontend_url}{next_path}?token={jwt_token}")
