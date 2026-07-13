"""Stage 2 — code structure analysis: languages and dependency manifests."""

from clients.github import get_repo_languages, get_repo_tree

DEPENDENCY_MANIFESTS = (
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
)


async def run_stage_2(github_url: str) -> str:
    """Summarize the repo's tech stack for the LLM scoring stage."""
    languages = await get_repo_languages(github_url)
    tree = await get_repo_tree(github_url)

    lang_summary = (
        ", ".join(sorted(languages, key=languages.get, reverse=True)[:5])
        or "none detected"
    )

    manifests = sorted(
        {
            path.rsplit("/", 1)[-1]
            for path in tree
            if path.rsplit("/", 1)[-1] in DEPENDENCY_MANIFESTS
        }
    )
    manifest_summary = ", ".join(manifests) if manifests else "none"

    return (
        f"Languages: {lang_summary}. "
        f"Files: {len(tree)}. "
        f"Dependency manifests: {manifest_summary}."
    )
