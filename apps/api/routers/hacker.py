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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="GitHub token expired; please re-authenticate",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub returned status {resp.status_code}",
        )

    return [
        {"name": repo["full_name"], "url": repo["html_url"]}
        for repo in resp.json()
    ]
