import json
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.schemas.plan_schema import Plan

_SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "planner_system.txt").read_text()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # drop opening fence line and closing fence line
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


async def run_planner(goal: str) -> Plan:
    """Generate a structured Plan from a user goal. Retries once on JSON parse failure."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=f"Goal: {goal}"),
    ]

    for attempt in range(2):  # max 1 retry
        response = await llm.ainvoke(messages)
        raw = _strip_code_fences(response.content)

        try:
            data = json.loads(raw)
            return Plan(**data)
        except Exception as exc:
            if attempt == 0:
                messages.append(AIMessage(content=response.content))
                messages.append(
                    HumanMessage(
                        content=(
                            "Your previous response could not be parsed as valid JSON. "
                            "Please respond with ONLY a valid JSON object matching the required schema, "
                            "with no markdown fences or extra text."
                        )
                    )
                )
            else:
                raise ValueError(
                    f"Planner failed to return valid JSON after retry: {exc}"
                ) from exc
