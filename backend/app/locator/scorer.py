from __future__ import annotations

import math
import re
from typing import Optional

from rapidfuzz import fuzz  # type: ignore

# ── Score weights ─────────────────────────────────────────────────────────────
# Weights are normalised at call time based on which signals are actually present.
W_TEXT = 0.45
W_ICON = 0.35
W_REGION = 0.10
W_ANCHOR = 0.10

NO_MATCH_THRESHOLD = 0.55

# ── Region boundaries (fraction of screen width / height) ─────────────────────
_REGION_BOUNDS: dict[str, tuple[float, float, float, float]] = {
    # (x_min, y_min, x_max, y_max)
    "top_left":     (0.00, 0.00, 0.33, 0.33),
    "top_right":    (0.66, 0.00, 1.00, 0.33),
    "bottom_left":  (0.00, 0.66, 0.33, 1.00),
    "bottom_right": (0.66, 0.66, 1.00, 1.00),
    "center":       (0.33, 0.33, 0.66, 0.66),
}


# ── Text matching ─────────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def text_match_score(target_text: str, raw_text: str) -> float:
    """Returns 0.0–1.0 similarity between target_text and raw_text."""
    t = _normalize(target_text)
    r = _normalize(raw_text)
    if not t or not r:
        return 0.0
    if t == r:
        return 1.0
    if t in r or r in t:
        return 0.9
    ratio = fuzz.ratio(t, r)
    if ratio >= 85:
        return ratio / 100.0
    return 0.0


# ── Region scoring ────────────────────────────────────────────────────────────

def region_score(
    candidate: dict,
    location_hint: Optional[str],
    img_w: int,
    img_h: int,
) -> float:
    """1.0 if candidate center is inside the hinted region, else 0.4."""
    if not location_hint or location_hint not in _REGION_BOUNDS:
        return 1.0  # no hint → neutral score
    bounds = _REGION_BOUNDS[location_hint]
    cx, cy = candidate["center_px"]
    cx_n, cy_n = cx / img_w, cy / img_h
    x_min, y_min, x_max, y_max = bounds
    if x_min <= cx_n <= x_max and y_min <= cy_n <= y_max:
        return 1.0
    return 0.4


# ── Anchor scoring ────────────────────────────────────────────────────────────

def _resolve_anchor(
    near_text: Optional[list[str]],
    ocr_candidates: list[dict],
    location_hint: Optional[str],
) -> tuple[float, float]:
    """
    Compute anchor point in normalised (0–1) coords.
    Priority: near_text OCR match → location_hint region center → screen center.
    """
    if near_text:
        for anchor_str in near_text:
            best_score = 0.0
            best_c: Optional[dict] = None
            for c in ocr_candidates:
                s = text_match_score(anchor_str, c["raw_text"])
                if s > best_score:
                    best_score = s
                    best_c = c
            if best_c and best_score >= 0.85:
                # Return normalised center — normalisation happens per candidate in caller
                return best_c["center_px"][0], best_c["center_px"][1]  # pixel, not norm yet

    if location_hint and location_hint in _REGION_BOUNDS:
        b = _REGION_BOUNDS[location_hint]
        # Return the region center in normalised coords (flag with a sentinel)
        return -(b[0] + b[2]) / 2, -(b[1] + b[3]) / 2  # negative = already normalised

    return -0.5, -0.5  # screen centre, pre-normalised


def anchor_score(
    candidate: dict,
    anchor: tuple[float, float],
    img_w: int,
    img_h: int,
) -> float:
    """
    1.0 at anchor; decays linearly with Euclidean distance (normalised).
    anchor is (px, py) in pixel coords if positive, or normalised coords (negative sentinel).
    """
    ax, ay = anchor
    # Normalise anchor
    if ax >= 0 and ay >= 0:
        ax_n, ay_n = ax / img_w, ay / img_h
    else:
        ax_n, ay_n = -ax, -ay  # already normalised (stored as negative)

    cx, cy = candidate["center_px"]
    cx_n, cy_n = cx / img_w, cy / img_h
    dist = math.sqrt((cx_n - ax_n) ** 2 + (cy_n - ay_n) ** 2)
    # max diagonal ≈ 1.41; map distance linearly: 0 → 1.0, 1.41 → ~0.0
    return max(0.0, 1.0 - dist)


# ── Combined scoring ──────────────────────────────────────────────────────────

def score_candidates(
    candidates: list[dict],
    target_text: Optional[str],
    icon_description: Optional[str],
    location_hint: Optional[str],
    near_text: Optional[list[str]],
    ocr_candidates: list[dict],
    img_w: int,
    img_h: int,
) -> list[dict]:
    """
    Score every candidate and return them sorted by total_score descending.
    Each returned candidate dict has a 'total_score' key added.
    """
    anchor = _resolve_anchor(near_text, ocr_candidates, location_hint)

    has_text = bool(target_text)
    has_icon = bool(icon_description)

    active_w_text = W_TEXT if has_text else 0.0
    active_w_icon = W_ICON if has_icon else 0.0
    active_w_region = W_REGION
    active_w_anchor = W_ANCHOR
    total_w = active_w_text + active_w_icon + active_w_region + active_w_anchor
    if total_w == 0:
        total_w = 1.0

    scored: list[dict] = []
    for c in candidates:
        ts = text_match_score(target_text or "", c["raw_text"]) if has_text else 0.0
        ic = c["scores"].get("icon", 0.0) if has_icon else 0.0
        rs = region_score(c, location_hint, img_w, img_h)
        ac = anchor_score(c, anchor, img_w, img_h)

        total = (
            active_w_text * ts
            + active_w_icon * ic
            + active_w_region * rs
            + active_w_anchor * ac
        ) / total_w

        c = dict(c)  # shallow copy so we don't mutate the original
        c["scores"] = {**c.get("scores", {}), "text": ts, "icon": ic, "region": rs, "anchor": ac}
        c["total_score"] = total
        scored.append(c)

    scored.sort(key=lambda c: c["total_score"], reverse=True)
    return scored
