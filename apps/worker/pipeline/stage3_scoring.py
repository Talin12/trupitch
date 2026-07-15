"""Stage 3 — LLM qualitative scoring against the campaign rubric.

The final stage: only reached after Stage 1 (repo exists) and Stage 2
(tech-stack summary) have both completed. This is the only stage that
costs an LLM call / can incur provider cost.
"""

from clients.llm import evaluate_pitch_and_code


async def run_stage_3(
    pitch: str, tech_summary: str, rules: list[dict]
) -> tuple[int, str]:
    """Score the submission. Returns (final_score 0-100, rationale).

    `rules` is the campaign's rubric as a list of
    {"description": str, "weight": float} dicts (loaded from the Rule
    table in tasks.py). The actual prompt construction, provider choice,
    and fallback-to-mock logic all live in clients/llm.py — this
    function is just the pipeline-stage wrapper tasks.py calls.
    """
    result = await evaluate_pitch_and_code(pitch, tech_summary, rules)
    return result["score"], result["rationale"]
