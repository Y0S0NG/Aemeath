import asyncio

from app.llm.guidance_chain import run_guidance
from app.locator.locator import locate
from app.locator.ocr_engine import run_ocr
from app.schemas.guidance_schema import ResolvedGuidanceResponse
from app.schemas.plan_schema import Plan


async def analyze_screenshot(
    plan: Plan,
    current_step_id: str,
    screenshot_b64: str,
) -> ResolvedGuidanceResponse:
    """
    Run Commander (LLM) and OCR in parallel, then pass results to the Locator.

    The OCR pre-computes all text boxes while waiting for the LLM response.
    Once both are ready, the Locator scores candidates and resolves a precise bbox.
    """
    (ocr_candidates, img_size), commander = await asyncio.gather(
        run_ocr(screenshot_b64),
        run_guidance(plan, current_step_id, screenshot_b64),
    )

    ui_target = locate(commander, ocr_candidates, img_size, screenshot_b64)

    return ResolvedGuidanceResponse(
        status=commander.status,
        confidence=commander.confidence,
        current_step_id=commander.current_step_id,
        step_done=commander.step_done,
        next_instruction=commander.next_instruction,
        ui_target=ui_target,
        notes=commander.notes,
    )
