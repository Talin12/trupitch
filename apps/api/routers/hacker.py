"""Endpoints for the authenticated hacker.

Everything here requires a valid session JWT (via the
get_current_hacker dependency) — there is no public/unauthenticated
route in this router.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from core.security import get_current_hacker
from models import Hacker

router = APIRouter(prefix="/hacker", tags=["hacker"])

GITHUB_REPOS_URL = "https://api.github.com/user/repos"


@router.get("/repos")
async def list_repos(
    hacker: Hacker = Depends(get_current_hacker),
) -> list[dict[str, str]]:
    """The hacker's GitHub repositories, most recently updated first.

    Powers the repo dropdown on EventPage.tsx: the hacker's own stored
    OAuth token (never sent to the frontend) is used server-side to ask
    GitHub for exactly the repos this account can see, so the dropdown
    only ever lists real, owned-or-collaborated-on repositories.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                GITHUB_REPOS_URL,
                params={"sort": "updated", "per_page": 100},
                headers={
                    "Authorization": f"Bearer {hacker.github_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub request failed: {exc}",
        )

    if resp.status_code == 401:
        # The stored GitHub token was revoked or expired; the hacker
        # needs to go through /auth/github/login again to get a fresh one.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub token expired; please re-authenticate",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub returned status {resp.status_code}",
        )

    # Trim GitHub's large repo payload down to just what the frontend
    # dropdown needs: a display name and the URL to submit.
    return [
        {"name": repo["full_name"], "url": repo["html_url"]}
        for repo in resp.json()
    ]
