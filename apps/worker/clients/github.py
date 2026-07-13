"""Lightweight async GitHub API client."""

import logging
import os
from urllib.parse import urlparse

import httpx

from clients.errors import RetryableError

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"

__all__ = [
    "RetryableError",
    "check_repo_exists",
    "get_repo_languages",
    "get_repo_tree",
    "parse_repo_path",
]


def parse_repo_path(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL, or None if it isn't one."""
    parsed = urlparse(url)
    if parsed.hostname not in ("github.com", "www.github.com"):
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return owner, repo


async def _get(path: str) -> httpx.Response:
    """GET a GitHub API path; raise RetryableError on transient failures."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "trupitch-worker",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            resp = await client.get(f"{GITHUB_API}{path}")
    except httpx.HTTPError as exc:
        raise RetryableError(f"GitHub request failed: {exc}") from exc

    if resp.status_code in (403, 429):
        raise RetryableError(f"GitHub rate limited ({resp.status_code}) on {path}")
    if resp.status_code >= 500:
        raise RetryableError(f"GitHub server error ({resp.status_code}) on {path}")
    return resp


def _repo_path_or_raise(url: str) -> tuple[str, str]:
    repo_path = parse_repo_path(url)
    if repo_path is None:
        raise ValueError(f"Not a GitHub repository URL: {url}")
    return repo_path


async def check_repo_exists(url: str) -> bool:
    """True if the repo exists and is visible, False if not (or not a repo URL)."""
    repo_path = parse_repo_path(url)
    if repo_path is None:
        return False
    owner, repo = repo_path

    resp = await _get(f"/repos/{owner}/{repo}")
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise RetryableError(
        f"Unexpected GitHub status {resp.status_code} for {owner}/{repo}"
    )


async def get_repo_languages(url: str) -> dict:
    """Language byte counts, e.g. {"Python": 12345, "TypeScript": 678}."""
    owner, repo = _repo_path_or_raise(url)
    resp = await _get(f"/repos/{owner}/{repo}/languages")
    if resp.status_code == 200:
        return resp.json()
    if resp.status_code == 404:
        return {}
    raise RetryableError(
        f"Unexpected GitHub status {resp.status_code} for {owner}/{repo} languages"
    )


async def get_repo_tree(url: str) -> list[str]:
    """All file paths in the repo at HEAD (empty list for empty/missing tree)."""
    owner, repo = _repo_path_or_raise(url)
    resp = await _get(f"/repos/{owner}/{repo}/git/trees/HEAD?recursive=1")
    if resp.status_code == 200:
        payload = resp.json()
        if payload.get("truncated"):
            logger.warning("Tree for %s/%s truncated by GitHub", owner, repo)
        return [
            item["path"]
            for item in payload.get("tree", [])
            if item.get("type") == "blob"
        ]
    if resp.status_code in (404, 409):  # 409: repository is empty
        return []
    raise RetryableError(
        f"Unexpected GitHub status {resp.status_code} for {owner}/{repo} tree"
    )
