"""Stage 1 — hard heuristics: cheap deterministic disqualification gates."""

from clients.github import check_repo_exists


async def run_stage_1(github_url: str) -> tuple[bool, str]:
    """Validate the submitted repository. Returns (passed, reason)."""
    if await check_repo_exists(github_url):
        return True, "Repo validated"
    return False, "Repository not found or private"
