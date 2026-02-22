from typing import Literal, Optional

from pydantic import BaseModel, Field

HintRegion = Literal["top_left", "top_right", "bottom_left", "bottom_right", "center"]
GuidanceStatus = Literal["on_track", "off_track", "uncertain"]


# ── Commander (LLM) output ────────────────────────────────────────────────────

class ElementTarget(BaseModel):
    """Semantic description of the UI element the user should interact with."""
    element_type: str                           # required: "button", "link", "input", etc.
    text: Optional[str] = None                  # visible text label
    icon_description: Optional[str] = None     # e.g. "plus icon", "gear icon"
    color: Optional[str] = None                # e.g. "blue", "red"
    location_hint: Optional[HintRegion] = None
    near_text: Optional[list[str]] = None       # anchor strings for distance scoring


class CommanderResponse(BaseModel):
    """Output of the LLM (Commander) — no bounding box."""
    status: GuidanceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    current_step_id: str
    step_done: bool
    next_instruction: str
    target: Optional[ElementTarget] = None      # None when off_track / uncertain
    notes: Optional[str] = None


# ── Locator / resolved output ─────────────────────────────────────────────────

class ResolvedUITarget(BaseModel):
    """Post-locator result with precise bbox."""
    hint_region: Optional[HintRegion] = None
    target_text: Optional[str] = None
    # [x1, y1, x2, y2] normalized 0–1; None when locator found no match
    bbox_norm: Optional[list[float]] = Field(default=None, min_length=4, max_length=4)
    locator_confidence: float = Field(ge=0.0, le=1.0)
    locator_method: str   # e.g. "ocr", "template", "none"


class ResolvedGuidanceResponse(BaseModel):
    """Final response sent to the frontend (post Commander + Locator)."""
    status: GuidanceStatus
    confidence: float = Field(ge=0.0, le=1.0)
    current_step_id: str
    step_done: bool
    next_instruction: str
    ui_target: Optional[ResolvedUITarget] = None
    notes: Optional[str] = None
