from clients.github import check_repo_exists


async def run_stage_1(github_url: str) -> tuple[bool, str]:
    if await check_repo_exists(github_url):
        return True, "Repo validated"
    return False, "Repository not found or private"
