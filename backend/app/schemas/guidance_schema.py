from typing import Literal, Optional
from pydantic import BaseModel, Field


HintRegion = Literal["top_left", "top_right", "bottom_left", "bottom_right", "center"]
GuidanceStatus = Literal["on_track", "off_track", "uncertain"]


class UITarget(BaseModel):
    hint_region: HintRegion
    target_text: str
    # [x1, y1, x2, y2] normalized 0–1 relative to screenshot dimensions
    bbox_norm: list[float] = Field(min_length=4, max_length=4)


class GuidanceResponse(BaseModel):
    status: GuidanceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    current_step_id: str
    # True only when status is "on_track" and the step's success criteria are met
    step_done: bool
    next_instruction: str
    # Omitted when status is "off_track" or "uncertain"
    ui_target: Optional[UITarget] = None
