from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.plan_schema import Plan
from app.services.planner_service import generate_plan

router = APIRouter(prefix="/plan", tags=["plan"])


class PlanRequest(BaseModel):
    goal: str


@router.post("/generate", response_model=Plan)
async def generate_plan_endpoint(request: PlanRequest) -> Plan:
    try:
        return await generate_plan(request.goal)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
