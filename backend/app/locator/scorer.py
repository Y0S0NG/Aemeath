from __future__ import annotations

import math
import re
from typing import Optional

from rapidfuzz import fuzz  # type: ignore

# ── Score weights ─────────────────────────────────────────────────────────────
# Weights are normalised at call time based on which signals are actually present.
W_TEXT   = 0.50
W_ICON   = 0.35
W_ANCHOR = 0.15

NO_MATCH_THRESHOLD = 0.55


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
    if ratio >= 80:
        return ratio / 100.0
    # Secondary check: token-level partial match catches OCR typos and
    # short-string transpositions that fuzz.ratio under-scores.
    partial = fuzz.partial_ratio(t, r)
    if partial >= 90:
        return partial / 100.0 * 0.75   # cap at 0.75 — below exact/substring tier
    return 0.0


# ── Anchor scoring ────────────────────────────────────────────────────────────

def _resolve_anchor(
    near_text: Optional[list[str]],
    ocr_candidates: list[dict],
) -> tuple[float, float]:
    """
    Compute anchor point in pixel coords from near_text OCR matches.
    Falls back to screen centre (returned as negative normalised sentinel) if
    no near_text match is found.
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
                return best_c["center_px"][0], best_c["center_px"][1]  # pixel coords

    return -0.5, -0.5  # screen centre, pre-normalised (negative sentinel)


def anchor_score(
    candidate: dict,
    anchor: tuple[float, float],
    img_w: int,
    img_h: int,
) -> float:
    """
    1.0 at anchor; decays linearly with Euclidean distance (normalised).
    anchor is (px, py) in pixel coords if both positive,
    or normalised coords when stored as negatives (sentinel).
    """
    ax, ay = anchor
    ax_n, ay_n = (-ax, -ay) if ax < 0 else (ax / img_w, ay / img_h)

    cx, cy = candidate["center_px"]
    cx_n, cy_n = cx / img_w, cy / img_h
    dist = math.sqrt((cx_n - ax_n) ** 2 + (cy_n - ay_n) ** 2)
    return max(0.0, 1.0 - dist)


# ── Combined scoring ──────────────────────────────────────────────────────────

def score_candidates(
    candidates: list[dict],
    target_text: Optional[str],
    icon_description: Optional[str],
    near_text: Optional[list[str]],
    ocr_candidates: list[dict],
    img_w: int,
    img_h: int,
) -> list[dict]:
    """
    Score every candidate and return them sorted by total_score descending.
    Each returned candidate dict has a 'total_score' key added.
    """
    anchor = _resolve_anchor(near_text, ocr_candidates)

    has_text = bool(target_text)
    has_icon = bool(icon_description)

    active_w_text   = W_TEXT   if has_text else 0.0
    active_w_icon   = W_ICON   if has_icon else 0.0
    active_w_anchor = W_ANCHOR
    total_w = active_w_text + active_w_icon + active_w_anchor
    if total_w == 0:
        total_w = 1.0

    scored: list[dict] = []
    for c in candidates:
        ts = text_match_score(target_text or "", c["raw_text"]) if has_text else 0.0
        ic = c["scores"].get("icon", 0.0) if has_icon else 0.0
        ac = anchor_score(c, anchor, img_w, img_h)

        total = (active_w_text * ts + active_w_icon * ic + active_w_anchor * ac) / total_w

        c = dict(c)  # shallow copy so we don't mutate the original
        c["scores"] = {**c.get("scores", {}), "text": ts, "icon": ic, "anchor": ac}
        c["total_score"] = total
        scored.append(c)

    scored.sort(key=lambda c: c["total_score"], reverse=True)
    return scored
