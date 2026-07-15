"""JWT session management for authenticated hackers.

Flow this module supports:
  1. routers/auth.py calls create_access_token() after a successful
     GitHub OAuth callback, and hands the resulting JWT to the frontend.
  2. The frontend stores that JWT and sends it back as
     `Authorization: Bearer <token>` on every authenticated request.
  3. Protected routes depend on get_current_hacker(), which decodes the
     JWT, looks up the Hacker row it names, and injects it into the
     handler — or raises 401 if anything about the token is wrong.

There is no server-side session store: the JWT itself, signed with
settings.jwt_secret, is the only proof of identity. Losing the secret
(or rotating it) invalidates every outstanding token at once.
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models import Hacker

# How long an issued session JWT remains valid before the hacker has to
# re-authenticate via GitHub.
TOKEN_TTL = timedelta(days=7)

# `auto_error=False` so a missing/absent Authorization header reaches our
# own code (get_current_hacker) as `credentials=None`, rather than FastAPI
# short-circuiting with its own generic 403 — we want a consistent 401
# with our own message across all "not authenticated" cases.
bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(hacker_id: int) -> str:
    """Mint a signed JWT that identifies this hacker for TOKEN_TTL."""
    now = datetime.now(timezone.utc)
    # "sub" (subject) is the JWT-standard claim for "who is this token
    # about"; we store the Hacker.id there, as a string per JWT convention.
    payload = {"sub": str(hacker_id), "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _unauthorized(detail: str) -> HTTPException:
    """Shared 401 builder so every failure mode below returns the same
    shape of error, including the WWW-Authenticate header browsers/clients
    expect on a bearer-auth failure.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_hacker(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Hacker:
    """FastAPI dependency: decode the bearer token and load the Hacker.

    Add `hacker: Hacker = Depends(get_current_hacker)` to any route to
    require a valid session; FastAPI runs this before the route body, so
    the handler only ever sees a real, currently-existing Hacker.
    """
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        # Raises jwt.InvalidTokenError for a bad signature, malformed
        # token, or an expired `exp` claim — all three fold into the same
        # generic 401 below so we don't leak *why* the token is bad.
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=["HS256"]
        )
        hacker_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _unauthorized("Invalid or expired token")

    # The token can be structurally valid yet point at a Hacker that no
    # longer exists (e.g. deleted); treat that the same as "not logged in".
    hacker = await db.get(Hacker, hacker_id)
    if hacker is None:
        raise _unauthorized("Unknown hacker")
    return hacker
