from __future__ import annotations

import logging
from typing import Optional

from app.schemas.guidance_schema import CommanderResponse, ResolvedUITarget
from app.locator.scorer import score_candidates, NO_MATCH_THRESHOLD
from app.locator.template_matcher import detect_icon

logger = logging.getLogger("app.locator")

# Module-level debug state — populated on every locate() call, read by test scripts.
last_scored_candidates: list[dict] = []

_SEP  = "─" * 64
_SEP2 = "━" * 64


def _log(msg: str) -> None:
    """Print to stdout and emit at INFO level so uvicorn captures it too."""
    print(f"[LOCATOR] {msg}")
    logger.info(msg)


def locate(
    commander: CommanderResponse,
    ocr_candidates: list[dict],
    img_size: tuple[int, int],
    screenshot_b64: str,
) -> Optional[ResolvedUITarget]:
    """
    Run the locator pipeline using pre-computed OCR candidates and the Commander result.

    Args:
        commander:      LLM output (Commander) describing WHAT to find.
        ocr_candidates: Text boxes already extracted from the screenshot via OCR.
        img_size:       (width, height) of the image space used by OCR candidates.
        screenshot_b64: Raw base64 screenshot (used for template matching).

    Returns:
        ResolvedUITarget with bbox_norm set to None when no confident match is found,
        or None when Commander provided no target at all.
    """
    _log(_SEP2)
    _log("Locator pipeline started")

    # ── Commander target ──────────────────────────────────────────────────────
    target = commander.target
    if not target:
        _log("Commander provided no target — skipping locator")
        _log(_SEP2)
        return None

    _log(f"Commander target:")
    _log(f"  text            : {target.text!r}")
    _log(f"  icon_description: {target.icon_description!r}")
    _log(f"  near_text       : {target.near_text}")
    _log(f"  element_type    : {target.element_type}")

    img_w, img_h = img_size
    _log(f"Image size        : {img_w}×{img_h} px")

    # ── Build candidate pool ──────────────────────────────────────────────────
    _log(_SEP)
    _log(f"Step 1 — Build candidate pool")
    _log(f"  OCR candidates  : {len(ocr_candidates)}")

    all_candidates: list[dict] = list(ocr_candidates)
    icon_count = 0

    if target.icon_description:
        _log(f"  Running template matcher for icon: {target.icon_description!r}")
        icon_cands = detect_icon(target.icon_description, screenshot_b64, img_size)
        icon_count = len(icon_cands)
        all_candidates.extend(icon_cands)
        _log(f"  Icon candidates : {icon_count}")
    else:
        _log("  Icon matching   : skipped (no icon_description)")

    _log(f"  Total pool size : {len(all_candidates)}")

    if not all_candidates:
        _log("  Pool is empty — returning no-match immediately")
        _log(_SEP2)
        return ResolvedUITarget(
            target_text=target.text,
            bbox_norm=None,
            locator_confidence=0.0,
            locator_method="none",
        )

    # ── Score candidates ──────────────────────────────────────────────────────
    _log(_SEP)
    _log("Step 2 — Score candidates")

    global last_scored_candidates
    scored = score_candidates(
        candidates=all_candidates,
        target_text=target.text,
        icon_description=target.icon_description,
        near_text=target.near_text,
        ocr_candidates=ocr_candidates,
        img_w=img_w,
        img_h=img_h,
    )
    last_scored_candidates = scored

    _log(f"  Scored {len(scored)} candidates — ranked by total_score:")
    _log(f"  {'#':<4} {'total':>6}  {'text':>6}  {'icon':>6}  {'anchor':>6}  {'src':<10}  label")
    _log(f"  {'─'*4} {'─'*6}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*10}  {'─'*30}")
    for i, c in enumerate(scored, 1):
        sc = c.get("scores", {})
        marker = " ◀ BEST" if i == 1 else ""
        _log(
            f"  {i:<4} {c['total_score']:>6.3f}  "
            f"{sc.get('text', 0.0):>6.3f}  "
            f"{sc.get('icon', 0.0):>6.3f}  "
            f"{sc.get('anchor', 0.0):>6.3f}  "
            f"{c['source']:<10}  "
            f"{c.get('raw_text', '')!r}{marker}"
        )

    # ── Best candidate decision ───────────────────────────────────────────────
    _log(_SEP)
    _log("Step 3 — Threshold check")
    best = scored[0]
    best_score = best["total_score"]
    _log(f"  Best score      : {best_score:.3f}")
    _log(f"  Threshold       : {NO_MATCH_THRESHOLD}")

    if best_score < NO_MATCH_THRESHOLD:
        _log(f"  Result          : NO MATCH  ({best_score:.3f} < {NO_MATCH_THRESHOLD})")
        _log(_SEP2)
        return ResolvedUITarget(
            target_text=target.text,
            bbox_norm=None,
            locator_confidence=round(best_score, 3),
            locator_method="none",
        )

    # ── Normalise bbox to 0–1 ────────────────────────────────────────────────
    _log(f"  Result          : MATCH  ({best_score:.3f} ≥ {NO_MATCH_THRESHOLD})")
    x1, y1, x2, y2 = best["bbox_px"]
    bbox_norm = [
        round(x1 / img_w, 4),
        round(y1 / img_h, 4),
        round(x2 / img_w, 4),
        round(y2 / img_h, 4),
    ]
    _log(f"  Matched text    : {best.get('raw_text')!r}")
    _log(f"  Source          : {best['source']}")
    _log(f"  bbox_px         : [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")
    _log(f"  bbox_norm       : {bbox_norm}")
    _log(_SEP2)

    return ResolvedUITarget(
        target_text=target.text or best.get("raw_text"),
        bbox_norm=bbox_norm,
        locator_confidence=round(best_score, 3),
        locator_method=best["source"],
    )
