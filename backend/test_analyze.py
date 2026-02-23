"""
Full end-to-end test for POST /guidance/analyze — runs the complete pipeline:
  OCR (EasyOCR) + LLM (Commander) in parallel → Locator scoring → ResolvedGuidanceResponse

Imports directly from production modules so it always reflects the latest schema.

Visualises both layers on the annotated image:
  - Bright bbox rect   : bbox_norm from the Locator (CV) — the precise match
  - Fallback dot       : drawn at screen centre when locator returned null
  - Status / confidence badges, next_instruction banner

Hard-coded plan: Deploy a GKE Kubernetes cluster (6 steps).

Usage:
    # Take a fresh screenshot (2 s delay to switch windows):
    python test_analyze.py

    # Use an existing image:
    python test_analyze.py --image path/to/screen.png

    # Test a specific step (default: s3 — Click Create cluster):
    python test_analyze.py --step s3

Output:
    analyze_result.png  — fully annotated image
    Terminal            — pretty-printed ResolvedGuidanceResponse JSON
"""

import argparse
import asyncio
import base64
import io
import json
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load OPENAI_API_KEY from backend/.env before any LangChain imports
load_dotenv(Path(__file__).parent / ".env")

import cv2
import numpy as np
from PIL import Image, ImageGrab

# ── Production imports — test always stays in sync with the real code ─────────
sys.path.insert(0, str(Path(__file__).parent))
from app.services.guidance_service import analyze_screenshot
from app.schemas.guidance_schema import ResolvedGuidanceResponse
from app.schemas.plan_schema import Plan, PlanStep
import app.locator.locator as _locator_module

# ── Hard-coded plan: Deploy a GKE Kubernetes cluster ─────────────────────────
PLAN = Plan(
    goal="Deploy a Kubernetes cluster on Google Kubernetes Engine (GKE)",
    assumptions=[
        "User is logged into Google Cloud Console",
        "A GCP project is already selected",
        "Billing is enabled on the project",
    ],
    steps=[
        PlanStep(
            id="s1",
            title="Navigate to Kubernetes Engine",
            success_criteria="The Kubernetes Engine section is visible in the left navigation sidebar",
        ),
        PlanStep(
            id="s2",
            title="Open the Clusters tab",
            success_criteria="The Clusters list tab is open, showing existing clusters or an empty state",
        ),
        PlanStep(
            id="s3",
            title="Click Create cluster",
            success_criteria="The 'Create cluster' button has been clicked and the cluster creation dialog or page is visible",
        ),
        PlanStep(
            id="s4",
            title="Choose cluster mode",
            success_criteria="Either 'Autopilot' or 'Standard' mode has been selected",
        ),
        PlanStep(
            id="s5",
            title="Configure cluster name and region",
            success_criteria="A cluster name has been entered and a region/zone has been selected",
        ),
        PlanStep(
            id="s6",
            title="Create the cluster",
            success_criteria="The 'Create' button has been clicked and cluster provisioning has started",
        ),
    ],
)

# ── Colours (BGR) ─────────────────────────────────────────────────────────────
_STATUS_COLOR = {
    "on_track":  (50, 200, 50),    # green
    "off_track": (50, 100, 250),   # orange
    "uncertain": (200, 200, 50),   # yellow
}
_LOCATOR_COLOR   = (255, 80, 20)   # cyan-blue — precise locator bbox
_FALLBACK_COLOR  = (0, 165, 255)   # orange dot — no-match fallback


# ── Image helpers ─────────────────────────────────────────────────────────────

def load_image_as_b64(image_path: str | None) -> tuple[str, np.ndarray]:
    if image_path:
        pil_img = Image.open(image_path).convert("RGB")
        print(f"Loaded image: {image_path}  ({pil_img.width}×{pil_img.height})")
    else:
        print("Taking screenshot in 2 seconds — switch to the window you want to test...")
        time.sleep(2)
        pil_img = ImageGrab.grab().convert("RGB")
        print(f"Screenshot captured: {pil_img.width}×{pil_img.height}")

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return b64, np.array(pil_img)


# ── Annotation ────────────────────────────────────────────────────────────────

def _put_label(img: np.ndarray, text: str, x: int, y: int,
               font_scale: float = 0.55, thickness: int = 1,
               fg: tuple = (255, 255, 255), bg: tuple = (0, 0, 0)) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    cv2.rectangle(img, (x - 3, y - th - 3), (x + tw + 3, y + baseline + 3), bg, cv2.FILLED)
    cv2.putText(img, text, (x, y), font, font_scale, fg, thickness, cv2.LINE_AA)


def draw_resolved(img: np.ndarray, response: ResolvedGuidanceResponse) -> np.ndarray:
    """
    Annotate image using only fields present in the production ResolvedGuidanceResponse schema.

    Locator layer:
      • Bright bbox + corner ticks + confidence label  (when bbox_norm is set)
      • Fallback dot at screen centre                  (when bbox_norm is null)

    Badges:
      • Status + LLM confidence   (top-right)
      • Locator method + conf     (below status badge)
      • notes                     (above bottom banner, if present)
      • next_instruction banner   (bottom)
    """
    h, w = img.shape[:2]
    annotated = img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX

    status_color = _STATUS_COLOR.get(response.status, (180, 180, 180))
    ui = response.ui_target

    # ── Locator bbox (precise match) ──────────────────────────────────────────
    if ui and ui.bbox_norm:
        x1n, y1n, x2n, y2n = ui.bbox_norm
        bx1, by1 = int(x1n * w), int(y1n * h)
        bx2, by2 = int(x2n * w), int(y2n * h)

        cv2.rectangle(annotated, (bx1, by1), (bx2, by2), _LOCATOR_COLOR, 3)

        # Corner ticks
        tick = 12
        for (cx, cy), (dx, dy) in [
            ((bx1, by1), (1, 1)), ((bx2, by1), (-1, 1)),
            ((bx1, by2), (1, -1)), ((bx2, by2), (-1, -1)),
        ]:
            cv2.line(annotated, (cx, cy), (cx + dx * tick, cy), _LOCATOR_COLOR, 4)
            cv2.line(annotated, (cx, cy), (cx, cy + dy * tick), _LOCATOR_COLOR, 4)

        conf_label = f"locator: {ui.locator_method}  conf={ui.locator_confidence:.2f}"
        _put_label(annotated, conf_label, bx1, max(by1 - 6, 18),
                   font_scale=0.55, thickness=1, fg=(255, 255, 255), bg=_LOCATOR_COLOR)

        if ui.target_text:
            _put_label(annotated, f'"{ui.target_text}"', bx1, by2 + 18,
                       font_scale=0.55, fg=(255, 255, 255), bg=(40, 40, 40))

    # ── Fallback dot at screen centre when locator found no match ─────────────
    elif ui and ui.bbox_norm is None:
        dot_x, dot_y = w // 2, h // 2
        cv2.circle(annotated, (dot_x, dot_y), 14, _FALLBACK_COLOR, -1)
        cv2.circle(annotated, (dot_x, dot_y), 14, (255, 255, 255), 2)
        no_match_label = f"no match  conf={ui.locator_confidence:.2f}"
        _put_label(annotated, no_match_label, dot_x + 18, dot_y + 6,
                   font_scale=0.5, fg=(255, 255, 255), bg=_FALLBACK_COLOR)

    # ── Status badge (top-right) ──────────────────────────────────────────────
    badge = f"{response.status.upper()}  LLM={response.confidence:.2f}"
    (bw, bh), _ = cv2.getTextSize(badge, font, 0.65, 2)
    bx = w - bw - 20
    by = 34
    cv2.rectangle(annotated, (bx - 8, by - bh - 8), (w - 8, by + 8), status_color, cv2.FILLED)
    cv2.putText(annotated, badge, (bx, by), font, 0.65, (0, 0, 0), 2, cv2.LINE_AA)

    # Locator badge (below status)
    if ui:
        loc_badge = f"locator={ui.locator_method}  conf={ui.locator_confidence:.2f}"
        (lbw, lbh), _ = cv2.getTextSize(loc_badge, font, 0.5, 1)
        lbx = w - lbw - 20
        lby = by + lbh + 18
        cv2.rectangle(annotated, (lbx - 6, lby - lbh - 6), (w - 8, lby + 6), (40, 40, 40), cv2.FILLED)
        cv2.putText(annotated, loc_badge, (lbx, lby), font, 0.5, (200, 200, 200), 1, cv2.LINE_AA)

    # ── notes (above bottom banner) ───────────────────────────────────────────
    if response.notes:
        _put_label(annotated, f"notes: {response.notes}", 10, h - 40,
                   font_scale=0.45, fg=(220, 220, 220), bg=(30, 30, 30))

    # ── next_instruction banner (bottom) ─────────────────────────────────────
    instr = f"  {response.next_instruction}"
    (iw, ih), _ = cv2.getTextSize(instr, font, 0.6, 1)
    cv2.rectangle(annotated, (0, h - ih - 20), (w, h), (20, 20, 20), cv2.FILLED)
    cv2.putText(annotated, instr, (8, h - 10), font, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

    return annotated


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="End-to-end test for /guidance/analyze pipeline")
    p.add_argument("--image", "-i", default=None,
                   help="Path to an existing screenshot PNG (default: take a screenshot)")
    p.add_argument("--step", "-s", default="s3",
                   help="current_step_id to test  (default: s3 — Click Create cluster)")
    return p.parse_args()


async def _run(args: argparse.Namespace) -> None:
    b64, orig_np = load_image_as_b64(args.image)

    print(f"\nPlan goal : {PLAN.goal}")
    print(f"Step ID   : {args.step}  —  "
          f"{next((s.title for s in PLAN.steps if s.id == args.step), '(unknown)')}")

    print("\nRunning analyze_screenshot()  [OCR + LLM in parallel → Locator]…")
    response: ResolvedGuidanceResponse = await analyze_screenshot(PLAN, args.step, b64)

    print("\n── ResolvedGuidanceResponse ───────────────────────────────────")
    print(json.dumps(response.model_dump(), indent=2))
    print("───────────────────────────────────────────────────────────────")

    # ── Top-5 locator candidates ──────────────────────────────────────────────
    top5 = _locator_module.last_scored_candidates[:5]
    if top5:
        print("\n── Top-5 Locator Candidates ────────────────────────────────────")
        print(f"{'#':<3} {'total':>6}  {'text':>6}  {'icon':>6}  {'anchor':>6}  {'src':<10}  text")
        print("─" * 72)
        for i, c in enumerate(top5, 1):
            sc = c.get("scores", {})
            print(
                f"{i:<3} {c['total_score']:>6.3f}  "
                f"{sc.get('text', 0.0):>6.3f}  "
                f"{sc.get('icon', 0.0):>6.3f}  "
                f"{sc.get('anchor', 0.0):>6.3f}  "
                f"{c['source']:<10}  "
                f"{c.get('raw_text', '')!r}"
            )
        print("────────────────────────────────────────────────────────────────")
    else:
        print("\n(No locator candidates — Commander returned no target)")

    orig_bgr    = cv2.cvtColor(orig_np, cv2.COLOR_RGB2BGR)
    annotated   = draw_resolved(orig_bgr, response)
    output_path = "analyze_result.png"
    cv2.imwrite(output_path, annotated)
    print(f"\nAnnotated image saved → {output_path}")

    subprocess.run(["open", output_path], check=False)


def main() -> None:
    asyncio.run(_run(parse_args()))


if __name__ == "__main__":
    main()
