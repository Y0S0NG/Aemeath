from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.guidance_schema import GuidanceResponse
from app.schemas.plan_schema import Plan
from app.services.guidance_service import analyze_screenshot

router = APIRouter(prefix="/guidance", tags=["guidance"])


class GuidanceRequest(BaseModel):
    plan: Plan
    current_step_id: str
    screenshot_b64: str  # base64-encoded PNG


@router.post("/analyze", response_model=GuidanceResponse)
async def analyze_screenshot_endpoint(request: GuidanceRequest) -> GuidanceResponse:
    return await analyze_screenshot(
        request.plan,
        request.current_step_id,
        request.screenshot_b64,
    )
