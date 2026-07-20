from clients.llm import evaluate_pitch_and_code


async def run_stage_3(
    pitch: str, tech_summary: str, rules: list[dict]
) -> tuple[int, str]:
    result = await evaluate_pitch_and_code(pitch, tech_summary, rules)
    return result["score"], result["rationale"]
