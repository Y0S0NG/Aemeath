from pydantic import BaseModel


class PlanStep(BaseModel):
    id: str
    title: str
    success_criteria: str


class Plan(BaseModel):
    goal: str
    assumptions: list[str] = []
    steps: list[PlanStep]
