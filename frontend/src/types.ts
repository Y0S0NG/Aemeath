// ---------------------------------------------------------------------------
// Plan types (mirrors backend/app/schemas/plan_schema.py)
// ---------------------------------------------------------------------------

export interface PlanStep {
  id: string;
  title: string;
  success_criteria: string;
}

export interface Plan {
  goal: string;
  assumptions: string[];
  steps: PlanStep[];
}

// ---------------------------------------------------------------------------
// Guidance types (mirrors backend/app/schemas/guidance_schema.py)
// ---------------------------------------------------------------------------

export type GuidanceStatus = "on_track" | "off_track" | "uncertain";

export interface UITarget {
  target_text?: string;
  /** [x1, y1, x2, y2] normalized 0–1; null when locator found no confident match */
  bbox_norm: [number, number, number, number] | null;
  /** Confidence of the CV locator (0–1), independent of LLM confidence */
  locator_confidence: number;
  /** Which method resolved the bbox: "ocr", "template", "none" */
  locator_method: string;
}

export interface GuidanceResponse {
  status: GuidanceStatus;
  confidence: number;
  current_step_id: string;
  /** True only when status is "on_track" and the step's success criteria are met */
  step_done: boolean;
  next_instruction: string;
  /** Present when status is "on_track" and a target was identified */
  ui_target?: UITarget;
  /** Optional extra context from the LLM */
  notes?: string;
}
