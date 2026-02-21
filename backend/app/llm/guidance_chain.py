import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.schemas.guidance_schema import GuidanceResponse
from app.schemas.plan_schema import Plan

_BASE_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "guidance_system.txt").read_text()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _uncertain_fallback(current_step_id: str) -> GuidanceResponse:
    return GuidanceResponse(
        status="uncertain",
        confidence=0.0,
        current_step_id=current_step_id,
        step_done=False,
        next_instruction="Unable to analyze the screenshot. Please try again.",
        ui_target=None,
    )


async def run_guidance(
    plan: Plan,
    current_step_id: str,
    screenshot_b64: str,
) -> GuidanceResponse:
    """
    Analyze a screenshot against the current step and return a GuidanceResponse.

    Args:
        plan: The full structured plan.
        current_step_id: ID of the step the user should currently be completing.
        screenshot_b64: Base64-encoded PNG screenshot of the user's screen.
    """
    system_content = (
        f"{_BASE_SYSTEM_PROMPT}\n\n"
        f"---\n"
        f"PLAN:\n{plan.model_dump_json(indent=2)}\n\n"
        f"CURRENT STEP ID: {current_step_id}"
    )

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}",
                        "detail": "high",
                    },
                },
                {
                    "type": "text",
                    "text": (
                        f"Current step ID: {current_step_id}\n\n"
                        "Analyze the screenshot and return your guidance JSON."
                    ),
                },
            ]
        ),
    ]

    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    try:
        response = await llm.ainvoke(messages)
        raw = _strip_code_fences(response.content)
        data = json.loads(raw)
        return GuidanceResponse(**data)
    except Exception:
        return _uncertain_fallback(current_step_id)
