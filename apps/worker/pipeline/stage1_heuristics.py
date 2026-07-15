"""Stage 1 — hard heuristics: cheap deterministic disqualification gates.

Runs before any expensive work (GitHub tree/language calls, an LLM
call), so a submission that fails here never costs more than one
GitHub API request. Called once per submission from
apps/worker/tasks.py's _evaluate().
"""

from clients.github import check_repo_exists


async def run_stage_1(github_url: str) -> tuple[bool, str]:
    """Validate the submitted repository. Returns (passed, reason).

    Today this is the entire heuristic: does the repo exist and resolve
    on GitHub. A failing result here sets the submission's status
    straight to "disqualified" and skips Stage 2 and Stage 3 entirely
    (see tasks.py) — there's no partial credit for a submission whose
    repo can't even be found.
    """
    if await check_repo_exists(github_url):
        return True, "Repo validated"
    return False, "Repository not found or private"
