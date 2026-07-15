"""Stage 2 — code structure analysis: languages and dependency manifests.

Only runs for submissions that passed Stage 1. Produces a short
plain-text summary (not a score) that both a human reading the
dashboard and the LLM in Stage 3 can use to judge whether the pitch
matches what was actually built.
"""

from clients.github import get_repo_languages, get_repo_tree

# Filenames recognized as "this project declares its dependencies
# somewhere" across the ecosystems TruPitch expects to see at a
# hackathon. Presence of any of these is a signal of a real, structured
# project rather than a handful of loose scripts.
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
    """Summarize the repo's tech stack for the LLM scoring stage.

    Returns one sentence-ish string like:
    "Languages: Python, TypeScript. Files: 142. Dependency manifests:
    package.json, requirements.txt." — this exact string is what gets
    stored (alongside the Stage 3 rationale) in Submission.notes, and
    what the dashboard shows under "Code structure" for an expanded row.
    """
    languages = await get_repo_languages(github_url)
    tree = await get_repo_tree(github_url)

    # Top 5 languages by byte count, most-used first; GitHub's languages
    # endpoint returns a dict of {language: byte_count}.
    lang_summary = (
        ", ".join(sorted(languages, key=languages.get, reverse=True)[:5])
        or "none detected"
    )

    # Scan every file path in the tree for a manifest filename match
    # (matching on the basename, not full path, so e.g. a nested
    # frontend/package.json still counts).
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
