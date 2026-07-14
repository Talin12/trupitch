"""LLM scoring client.

Provider-agnostic via the OpenAI-compatible chat completions API:
  - LLM_BASE_URL  empty -> api.openai.com; or e.g. https://router.huggingface.co/v1
  - LLM_API_KEY   key for that provider (falls back to OPENAI_API_KEY only
                  when no custom base URL is set)
  - LLM_MODEL     model id, e.g. gpt-4o-mini or Qwen/Qwen2.5-7B-Instruct

Falls back to a deterministic mock whenever the provider is unusable
(no key, invalid key, exhausted credits) so the pipeline always completes.
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

LLM_TIMEOUT_SECONDS = 60.0

SYSTEM_PROMPT = """\
You are a strict hackathon judge. Score how well a project submission \
(pitch + tech stack) satisfies the organizer's judging rules.

Respond with ONLY a JSON object, no markdown fences, no extra text:
{"score": <integer 0-100>, "rationale": "<2-3 sentence justification>"}

Weigh each rule by its weight. Be skeptical of vague pitches that do not \
match the observed tech stack."""


def _llm_config() -> tuple[str | None, str | None, str]:
    """(api_key, base_url, model) resolved from the environment at call time."""
    base_url = os.getenv("LLM_BASE_URL") or None
    if base_url:
        api_key = os.getenv("LLM_API_KEY") or None
    else:
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or None
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    return api_key, base_url, model


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


def _extract_json(raw: str) -> str:
    """Tolerate markdown fences and prose around the JSON object."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        return raw[start : end + 1]
    return raw


def _parse_result(raw: str) -> dict:
    try:
        data = json.loads(_extract_json(raw))
        score = int(data["score"])
        rationale = str(data["rationale"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        # Malformed model output is transient; a retry usually fixes it.
        raise RetryableError(f"LLM returned unparseable result: {raw!r}") from exc
    return {"score": max(0, min(100, score)), "rationale": rationale}


def _mock_evaluation(
    pitch: str,
    tech_stack: str,
    rules: list[dict],
    reason: str = "no LLM key configured",
) -> dict:
    """Deterministic stand-in used when the real LLM is unavailable."""
    # Crude signal: longer pitches and richer stacks score higher.
    score = min(100, 40 + min(len(pitch) // 50, 30) + min(len(tech_stack) // 20, 30))
    return {
        "score": score,
        "rationale": (
            f"[mock evaluation — {reason}] Scored against "
            f"{len(rules)} rule(s) using pitch length and stack richness."
        ),
    }


async def evaluate_pitch_and_code(
    pitch: str, tech_stack: str, rules: list[dict]
) -> dict:
    """Score a submission. Returns {"score": int 0-100, "rationale": str}."""
    api_key, base_url, model = _llm_config()
    if not api_key or openai is None:
        if openai is None and api_key:
            logger.warning("LLM key set but openai SDK not installed")
        return _mock_evaluation(pitch, tech_stack, rules)

    client = openai.AsyncOpenAI(
        api_key=api_key, base_url=base_url, timeout=LLM_TIMEOUT_SECONDS
    )
    request: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(pitch, tech_stack, rules)},
        ],
    }
    if base_url is None:
        # Native OpenAI JSON mode; third-party providers vary in support,
        # so elsewhere we rely on the prompt + tolerant parsing.
        request["response_format"] = {"type": "json_object"}

    try:
        response = await client.chat.completions.create(**request)
    except openai.RateLimitError as exc:
        # Quota exhaustion is a billing state, not a transient blip.
        if "insufficient_quota" in str(exc):
            logger.warning("LLM quota exhausted; using mock evaluation")
            return _mock_evaluation(
                pitch, tech_stack, rules, reason="LLM quota exhausted"
            )
        raise RetryableError(f"LLM rate limited: {exc}") from exc
    except (openai.APITimeoutError, openai.APIConnectionError) as exc:
        raise RetryableError(f"LLM request failed transiently: {exc}") from exc
    except openai.APIStatusError as exc:
        if exc.status_code >= 500:
            raise RetryableError(f"LLM server error: {exc}") from exc
        # 4xx (bad key, no credits, unknown model): permanent for this config.
        # Complete the pipeline with the mock rather than stranding the
        # submission in 'evaluating'.
        logger.warning("LLM provider rejected request (%s): %s", exc.status_code, exc)
        return _mock_evaluation(
            pitch,
            tech_stack,
            rules,
            reason=f"LLM provider error {exc.status_code}",
        )
    finally:
        await client.close()

    return _parse_result(response.choices[0].message.content or "")
