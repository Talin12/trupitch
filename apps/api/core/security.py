import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models import Hacker, Organizer

TOKEN_TTL = timedelta(days=7)

bearer_scheme = HTTPBearer(auto_error=False)

_PBKDF2_ROUNDS = 390000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return "$".join(
        [
            "pbkdf2_sha256",
            str(_PBKDF2_ROUNDS),
            base64.b64encode(salt).decode(),
            base64.b64encode(dk).decode(),
        ]
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, rounds, salt_b64, hash_b64 = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
    return hmac.compare_digest(dk, expected)


def create_access_token(hacker_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(hacker_id),
        "typ": "hacker",
        "iat": now,
        "exp": now + TOKEN_TTL,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_organizer_token(organizer_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(organizer_id),
        "typ": "organizer",
        "iat": now,
        "exp": now + TOKEN_TTL,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode(credentials: HTTPAuthorizationCredentials | None, expected_typ: str) -> int:
    if credentials is None:
        raise _unauthorized("Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=["HS256"]
        )
        subject_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _unauthorized("Invalid or expired token")
    # A token minted for one audience must not authenticate the other. Older
    # hacker tokens carry no "typ"; treat a missing typ as "hacker".
    if payload.get("typ", "hacker") != expected_typ:
        raise _unauthorized("Invalid or expired token")
    return subject_id


async def get_current_hacker(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Hacker:
    hacker_id = _decode(credentials, "hacker")
    hacker = await db.get(Hacker, hacker_id)
    if hacker is None:
        raise _unauthorized("Unknown hacker")
    return hacker


async def get_current_organizer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Organizer:
    organizer_id = _decode(credentials, "organizer")
    organizer = await db.get(Organizer, organizer_id)
    if organizer is None:
        raise _unauthorized("Unknown organizer")
    return organizer
