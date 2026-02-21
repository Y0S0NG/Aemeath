from app.llm.planner_chain import run_planner
from app.schemas.plan_schema import Plan


async def generate_plan(goal: str) -> Plan:
    return await run_planner(goal)
