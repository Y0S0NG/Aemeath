from __future__ import annotations

from typing import Optional

from app.schemas.guidance_schema import CommanderResponse, ResolvedUITarget
from app.locator.scorer import score_candidates, NO_MATCH_THRESHOLD
from app.locator.template_matcher import detect_icon


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
    target = commander.target
    if not target:
        return None

    img_w, img_h = img_size

    # ── Build candidate pool ──────────────────────────────────────────────────
    all_candidates: list[dict] = list(ocr_candidates)

    if target.icon_description:
        icon_cands = detect_icon(target.icon_description, screenshot_b64, img_size)
        all_candidates.extend(icon_cands)

    if not all_candidates:
        return ResolvedUITarget(
            hint_region=target.location_hint,
            target_text=target.text,
            bbox_norm=None,
            locator_confidence=0.0,
            locator_method="none",
        )

    # ── Score candidates ──────────────────────────────────────────────────────
    scored = score_candidates(
        candidates=all_candidates,
        target_text=target.text,
        icon_description=target.icon_description,
        location_hint=target.location_hint,
        near_text=target.near_text,
        ocr_candidates=ocr_candidates,
        img_w=img_w,
        img_h=img_h,
    )

    best = scored[0]

    # ── No-match fallback ─────────────────────────────────────────────────────
    if best["total_score"] < NO_MATCH_THRESHOLD:
        return ResolvedUITarget(
            hint_region=target.location_hint,
            target_text=target.text,
            bbox_norm=None,
            locator_confidence=round(best["total_score"], 3),
            locator_method="none",
        )

    # ── Normalise bbox to 0–1 ────────────────────────────────────────────────
    x1, y1, x2, y2 = best["bbox_px"]
    bbox_norm = [
        round(x1 / img_w, 4),
        round(y1 / img_h, 4),
        round(x2 / img_w, 4),
        round(y2 / img_h, 4),
    ]

    return ResolvedUITarget(
        hint_region=target.location_hint,
        target_text=target.text or best.get("raw_text"),
        bbox_norm=bbox_norm,
        locator_confidence=round(best["total_score"], 3),
        locator_method=best["source"],
    )
