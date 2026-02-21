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

export type HintRegion =
  | "top_left"
  | "top_right"
  | "bottom_left"
  | "bottom_right"
  | "center";

export type GuidanceStatus = "on_track" | "off_track" | "uncertain";

export interface UITarget {
  hint_region: HintRegion;
  target_text: string;
  /** [x1, y1, x2, y2] normalized 0–1 relative to screenshot dimensions */
  bbox_norm: [number, number, number, number];
}

export interface GuidanceResponse {
  status: GuidanceStatus;
  confidence: number;
  current_step_id: string;
  /** True only when status is "on_track" and the step's success criteria are met */
  step_done: boolean;
  next_instruction: string;
  /** Omitted when status is "off_track" or "uncertain" */
  ui_target?: UITarget;
}
