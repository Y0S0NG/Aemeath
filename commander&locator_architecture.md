# Commander & Locator Architecture

LLM is good at deciding
+ What UI element the user should interact with.

However, it is bad at
+ Locate exactly where the element is.

Therefore, instead of throw the screenshot to a mutli-modal LLM (even a strong model), and let it configure the boundary box, I come up with the following architecture:
+ Let the LLM describe the UI element the user should interact with, very detailedly.
+ Pass the description to the Locator Module, which is made up of CV model(s), E.g OCR model

The updated architecture should look like this:
```
Electron overlay
   ↓
Screenshot capture
   ↓
Python backend
   ├── LLM reasoning (WHAT)
   └── Locator engine (WHERE)
          ├── OCR
          ├── OpenCV
          ├── Matching logic
          └── Accessibility (future)
   ↓
Precise bbox
   ↓
Overlay highlight
```

## Example Commander(LLM) output:
```
{
  "target": {
    "element_type": "button",
    "text": "Create",
    "icon_description": "plus icon",
    "color": "blue",
    "location_hint": "top right",
    "near_text": "Clusters"
  }
}
```

## Pseudo Locator Pipeline
```
def locate(target, screenshot):

    candidates = []

    # Step 1: OCR text match
    if target.text:
        candidates += find_text(target.text)

    # Step 2: icon detection
    if target.icon_description:
        candidates += detect_icon(target.icon_description)

    # Step 3: region filter
    candidates = filter_by_region(candidates, target.location_hint)

    # Step 4: choose best
    return best_bbox
```

## Visual detection strategy
+ Text Detection
    + OCR - detect text
+ Icon Detection
    + icon library + OpenCV template matching
    + Use CLIP model:
        1.	Extract patches across screen
        2.	Encode each patch
        3.	Compare with
    icon

## Final Selection
```
score = text_match_score
 + icon_similarity
 + distance_to_anchor
 + region_match
 + size_similarity
```


# Clarification regard the questions:
## 1. Commander output schema — what does the LLM now return?
Recommendation (cleanest): keep the same top-level GuidanceResponse, but replace ui_target with a semantic target and remove bbox from the Commander output.

Commander (LLM) output (NO bbox):
```
{
  "status": "on_track",
  "confidence": 0.78,
  "current_step_id": "s2",
  "step_done": false,
  "next_instruction": "Click the Create cluster button.",
  "target": {
    "element_type": "button",
    "text": "Create",
    "icon_description": null,
    "color": "blue",
    "location_hint": "top_right",
    "near_text": ["Clusters", "Kubernetes Engine"]
  },
  "notes": "If you don't see Create, open the Clusters page."
}
```
Then the backend returns to frontend a ResolvedGuidanceResponse (post-locator) that contains bbox:

Resolved output (what UI consumes):

```
{
  "status": "on_track",
  "confidence": 0.78,
  "current_step_id": "s2",
  "step_done": false,
  "next_instruction": "Click the Create cluster button.",
  "ui_target": {
    "hint_region": "top_right",
    "target_text": "Create",
    "bbox_norm": [0.74, 0.12, 0.93, 0.20],
    "locator_confidence": 0.91,
    "locator_method": "ocr+contour"
  },
  "notes": "..."
}
```

Are all target fields required?

No. Make them optional except element_type. Minimum viable set:
	•	Required: element_type
	•	Optional (but recommended): text, location_hint
	•	Optional: icon_description, color, near_text

Why: many elements are icon-only; sometimes the LLM can’t infer color; sometimes there’s no good anchor text.

Rule of thumb: at least one of text or icon_description should be present; otherwise locator will mostly rely on region+shape/cursor assist.

## 3. How is near_text used in scoring?

Anchor = the bbox center of the OCR match for near_text.

Implementation:
1. OCR all text boxes on screen.
2. For each string in near_text (allow list), find best OCR match (fuzzy).
3. If found, compute anchor point = center of its bbox.
4. Candidate’s distance_to_anchor = normalized distance between candidate center and anchor.
5. Convert distance to a score.

If no near_text found, fall back anchor center = center of the location_hint region (see #7). If that’s unknown, use screen center.

## 4. OCR library choice (which one?)

For your use case (desktop screenshots, CPU, near real-time), I recommend:

✅ PaddleOCR (recommended)
+ Good accuracy on UI text
+ Typically faster than EasyOCR on CPU in practice
+ Better layout/text-line handling

When to use EasyOCR
+ Quick “pip install” prototyping
+ You accept slower inference

When to use pytesseract
+ Only if you must keep deps tiny and can manage system install
+ Expect more missed UI text unless tuned

MVP pick: PaddleOCR.

(Implementation detail: use English model; optionally enable angle classification for rotated/tilted text.)

## 5. Icon detection — which approach?

Given performance + dependency realities:

MVP: Template matching first, with a small curated icon set + fallbacks
	•	Implement A now
	•	Defer CLIP unless you later need broad icon coverage

Why not CLIP first?
	•	PyTorch heavy
	•	CPU-only is slow, patch search is expensive
	•	Adds a lot of engineering for weekend MVP

Recommended chain (later-ready):
	1.	OCR match (text)
	2.	Template match (icon)
	3.	UI-shape detection (button-like contours)
	4.	Cursor-assisted fallback (ask user to hover)

If later you want CLIP: add as optional “expert mode” behind a config flag.

Icon pack suggestion: don’t overthink it for MVP.
	•	Start with 10–20 “navigation icons”: plus, gear, search, kebab menu, pencil/edit, trash, download, upload, filter, refresh, back arrow, help.
	•	Collect templates from real screenshots (AWS/GCP/GitHub) in both light/dark if needed.
	•	Store as PNG with alpha.

Font Awesome SVG rendered to PNG can work, but real UI icons often differ. Real screenshot templates are more robust.

## 6.Candidate format out of find_text() / detect_icon()

Use pixel coordinates internally for CV work, then convert to normalized at the end.

Internal candidate (pixel):
```
{
  "bbox_px": [x1, y1, x2, y2],
  "center_px": [cx, cy],
  "source": "ocr",
  "raw_text": "Create",
  "scores": { "text": 0.92, "region": 0.8, "anchor": 0.6 }
}
```
Final output to overlay: bbox_norm (consistent with your existing overlay schema).

This makes contour refinement and cropping straightforward.

## 7.filter_by_region thresholds

Do soft scoring, not hard filtering. Hard filters cause “no candidates” too often.

Region definition (simple and effective):
	•	Split screen into thirds for better precision than halves:

For width W, height H:
	•	left: x ∈ [0, 0.33W]
	•	center: x ∈ [0.33W, 0.66W]
	•	right: x ∈ [0.66W, W]
	•	top: y ∈ [0, 0.33H]
	•	middle: y ∈ [0.33H, 0.66H]
	•	bottom: y ∈ [0.66H, H]

So top_right = top third AND right third.

Soft score idea:

region_score = 1.0 if candidate center is inside region; else region_score = exp(-d/σ) where d is distance to region center normalized to [0..1].

MVP simplification:
	•	inside region: region_score = 1.0
	•	outside region: region_score = 0.4

## 8. Final score weights + size_similarity

Weights (not equal)

Text match should dominate when text exists.

Recommended weights:
	•	text_match_score: 0.45
	•	icon_similarity: 0.35
	•	region_match: 0.10
	•	distance_to_anchor: 0.10
	•	size_similarity: 0.00–0.05 (optional, low priority)

size_similarity: similar to what expected size?

Don’t use it unless you have a reference. In this architecture, Commander does not output size, so:
	•	Either drop size_similarity for MVP
	•	Or use a weak heuristic per element type:
	•	buttons have typical height range (e.g., 24–80 px on common UIs)
	•	icons 12–64 px
This is fragile across scaling, so keep it low weight.

“No match found” threshold

Return “no match” if:
	•	best_total_score < 0.55 (tune)
	•	OR if confidence gap between #1 and #2 is tiny and both low-quality (ambiguous)

## 9. No-match fallback behavior

Don’t throw an error; keep guidance alive.

Return a resolved response with no bbox, but still provide:
	•	hint region
	•	target_text/icon_description
	•	instruction
	•	and a “locator_confidence” low

```
{
  "ui_target": {
    "hint_region": "top_right",
    "target_text": "Create",
    "bbox_norm": null,
    "locator_confidence": 0.18,
    "locator_method": "none"
  },
  "status": "on_track",
  "step_done": false,
  "next_instruction": "Look for the Create button near the top right."
}
```
Then apply fallback policy:
	1.	Retry locator once with relaxed matching (see #10)
	2.	If still no match: show region arrow only + optionally ask for cursor assist:
	•	“Hover near the Create button and press Hotkey”

No need to change status to error; status is about workflow alignment, not locator success.

## 10. Text matching — exact or fuzzy?

Use fuzzy matching by default with guardrails.

Suggested rule:
	•	Normalize: lowercase, strip punctuation, collapse spaces
	•	Prefer exact match first
	•	If no exact, use fuzzy with threshold ≥ 85
	•	Also allow substring containment:
	•	target “Create” should match “Create cluster” if that’s the only candidate
	•	Penalize partial matches if there are better exact matches.

Practical scoring:
	•	exact match: 1.0
	•	substring match: 0.9
	•	fuzzy ratio/100: e.g. 0.86
	•	apply a small penalty if candidate contains extra words and there are multiple candidates

This handles real UI variations (“Create cluster”, “Create repository”, etc.)

## 11.Performance budget + parallelism

With 5-second capture interval, budget is:

Aim for ≤ 1.5s end-to-end locator on CPU, ideally ≤ 0.7s.

Reality:
	•	PaddleOCR can be ~0.2–1.2s depending on resolution and CPU
	•	Template matching is fast if limited templates and cropped search areas

Should Locator run parallel with LLM?

No, not in the strict Commander→Locator design, because Locator depends on Commander’s target description.

But you can overlap work intelligently:

Pipeline overlap strategy:
	1.	While waiting for Commander LLM:
	•	downscale screenshot
	•	run OCR once and cache results for this frame (or every other frame)
	2.	When Commander returns:
	•	do matching/scoring immediately using cached OCR boxes (fast)
	•	only run contour refinement on the best candidate region (cheap)

This gives you “parallel-ish” performance without complexity.

Critical optimization: do not OCR full 4K every frame.
	•	Downscale to e.g. width 1280 or 1440 for OCR.
	•	Keep original resolution only for contour refinement around the chosen candidate.