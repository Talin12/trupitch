"""LLM scoring client.

Uses the OpenAI API when OPENAI_API_KEY is set; otherwise falls back to a
deterministic mock so the pipeline stays runnable in local development.
"""

import json
import logging
import os

from clients.errors import RetryableError

try:
    import openai
except ImportError:  # SDK optional in mock-only environments
    openai = None

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT_SECONDS = 30.0

SYSTEM_PROMPT = """\
You are a strict hackathon judge. Score how well a project submission \
(pitch + tech stack) satisfies the organizer's judging rules.

Respond with ONLY a JSON object, no markdown fences, no extra text:
{"score": <integer 0-100>, "rationale": "<2-3 sentence justification>"}

Weigh each rule by its weight. Be skeptical of vague pitches that do not \
match the observed tech stack."""


def _build_user_prompt(pitch: str, tech_stack: str, rules: list[dict]) -> str:
    rules_text = (
        "\n".join(
            f"- (weight {r.get('weight', 1.0)}) {r.get('description', '')}"
            for r in rules
        )
        or "- (weight 1.0) General quality, originality, and technical depth"
    )
    return (
        f"## Judging rules\n{rules_text}\n\n"
        f"## Observed tech stack\n{tech_stack}\n\n"
        f"## Team pitch\n{pitch}"
    )


def _parse_result(raw: str) -> dict:
    try:
        data = json.loads(raw)
        score = int(data["score"])
        rationale = str(data["rationale"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        # Malformed model output is transient; a retry usually fixes it.
        raise RetryableError(f"LLM returned unparseable result: {raw!r}") from exc
    return {"score": max(0, min(100, score)), "rationale": rationale}


def _mock_evaluation(pitch: str, tech_stack: str, rules: list[dict]) -> dict:
    """Deterministic stand-in used when no API key is configured."""
    # Crude signal: longer pitches and richer stacks score higher.
    score = min(100, 40 + min(len(pitch) // 50, 30) + min(len(tech_stack) // 20, 30))
    return {
        "score": score,
        "rationale": (
            f"[mock evaluation — no LLM key configured] Scored against "
            f"{len(rules)} rule(s) using pitch length and stack richness."
        ),
    }


async def evaluate_pitch_and_code(
    pitch: str, tech_stack: str, rules: list[dict]
) -> dict:
    """Score a submission. Returns {"score": int 0-100, "rationale": str}."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or openai is None:
        if openai is None and api_key:
            logger.warning("OPENAI_API_KEY set but openai SDK not installed")
        return _mock_evaluation(pitch, tech_stack, rules)

    client = openai.AsyncOpenAI(api_key=api_key, timeout=LLM_TIMEOUT_SECONDS)
    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_user_prompt(pitch, tech_stack, rules),
                },
            ],
        )
    except (openai.APITimeoutError, openai.RateLimitError, openai.APIConnectionError) as exc:
        raise RetryableError(f"LLM request failed transiently: {exc}") from exc
    except openai.APIStatusError as exc:
        if exc.status_code >= 500:
            raise RetryableError(f"LLM server error: {exc}") from exc
        raise  # 4xx (bad key, bad model) is permanent: fail loudly, don't retry
    finally:
        await client.close()

    return _parse_result(response.choices[0].message.content or "")
