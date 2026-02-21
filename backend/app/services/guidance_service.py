from app.llm.guidance_chain import run_guidance
from app.schemas.guidance_schema import GuidanceResponse
from app.schemas.plan_schema import Plan


async def analyze_screenshot(
    plan: Plan,
    current_step_id: str,
    screenshot_b64: str,
) -> GuidanceResponse:
    return await run_guidance(plan, current_step_id, screenshot_b64)
