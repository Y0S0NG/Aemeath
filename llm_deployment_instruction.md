# Chat model - Planner Module
## 1. Responsibility
+ Generate structured plan from user's goal

## 2. Output (json)
```
{
  "goal": "...",
  "assumptions": [],
  "steps": [
    { "id": "s1", "title": "...", "success_criteria": "..." }
  ]
}
```
## 3. Implementation Steps
1. Create LangChain ChatModel using OpenAI GPT-4o
2. Create structured system prompt
3. Use Pydantic schema for validation
4. Add JSON parse retry (max 1 retry)
5. Return validated plan

# Multimodal model - Guidance Module
## 1. Responsibility
+ Based on the plans and screenshot, generate UI overlay configuration

## 2. Output (json)
```
{
  "status": "on_track",      // "on_track" | "off_track" | "uncertain"
  "confidence": 0.85,
  "current_step_id": "s2",
  "step_done": false,        // true → frontend auto-advances to next step (only when status is "on_track")
  "next_instruction": "Click the Create button.",
  "ui_target": {
    "hint_region": "top_right",   // valid: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center"
    "target_text": "Create",
    "bbox_norm": [0.7, 0.1, 0.9, 0.2]  // [x1, y1, x2, y2], normalized 0–1 relative to screenshot dimensions
  }
}
```

### `status` field semantics
- `"on_track"` — the screenshot contains the expected UI elements for the current step (user is on the correct page)
- `"off_track"` — the screenshot does NOT contain the expected elements (user is on the wrong page); `next_instruction` should provide navigation guidance back to the correct page; step does NOT auto-advance until status returns to `"on_track"`
- `"uncertain"` — fallback value used when LLM output cannot be parsed

## 3. Implementation Steps
1. Create multi-modal LangChain message using OpenAI GPT-4o
2. Attach screenshot as base64-encoded image content in the user message
3. Inject plan context (full plan JSON) as the system prompt
4. Ask model to:
    + Detect whether current page matches the expected step (→ `status`)
    + Provide next instruction (or navigation instruction if `off_track`)
    + Localize the target UI region (`bbox_norm` as `[x1, y1, x2, y2]` normalized 0–1)
5. Validate output with Pydantic
6. Fallback to `status: "uncertain"` if parse fails
