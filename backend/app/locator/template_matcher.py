from __future__ import annotations

import base64
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_ICONS_DIR = Path(__file__).parent / "icons"
_MATCH_THRESHOLD = 0.65  # normalized cross-correlation threshold


def _load_templates() -> dict[str, list[np.ndarray]]:
    """Load all PNG icon templates from the icons/ directory as grayscale arrays."""
    templates: dict[str, list[np.ndarray]] = {}
    if not _ICONS_DIR.exists():
        return templates

    for path in _ICONS_DIR.glob("*.png"):
        name = path.stem  # e.g. "plus", "gear", "search"
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        channels = img.shape[2] if img.ndim == 3 else 1
        bgr = img[:, :, :3] if channels >= 3 else img
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        templates.setdefault(name, []).append(gray)

    return templates


_templates: dict[str, list[np.ndarray]] | None = None


def _get_templates() -> dict[str, list[np.ndarray]]:
    global _templates
    if _templates is None:
        _templates = _load_templates()
    return _templates


def _screen_to_gray(screenshot_b64: str, img_size: tuple[int, int]) -> np.ndarray:
    """Decode the screenshot and resize to img_size, returning a grayscale array."""
    img_bytes = base64.b64decode(screenshot_b64)
    pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img_size
    pil_img = pil_img.resize((w, h), Image.LANCZOS)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)


def _nms(candidates: list[dict], iou_threshold: float = 0.5) -> list[dict]:
    """Greedy non-maximum suppression to remove heavily overlapping detections."""
    if not candidates:
        return candidates
    candidates = sorted(candidates, key=lambda c: c["scores"].get("icon", 0), reverse=True)
    kept: list[dict] = []
    for c in candidates:
        b = c["bbox_px"]
        overlap = False
        for k in kept:
            kb = k["bbox_px"]
            ix1 = max(b[0], kb[0])
            iy1 = max(b[1], kb[1])
            ix2 = min(b[2], kb[2])
            iy2 = min(b[3], kb[3])
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                area_b = (b[2] - b[0]) * (b[3] - b[1])
                area_kb = (kb[2] - kb[0]) * (kb[3] - kb[1])
                iou = inter / (area_b + area_kb - inter + 1e-6)
                if iou > iou_threshold:
                    overlap = True
                    break
        if not overlap:
            kept.append(c)
    return kept


def detect_icon(
    icon_description: str,
    screenshot_b64: str,
    img_size: tuple[int, int],
) -> list[dict]:
    """
    Match icon templates against the screenshot using normalized cross-correlation.

    Args:
        icon_description: Text description like "plus icon", "gear icon".
        screenshot_b64:   Base64-encoded screenshot PNG.
        img_size:         (width, height) of the downscaled image space to search in.

    Returns:
        List of candidate dicts in the same format as OCR candidates.
    """
    templates = _get_templates()
    if not templates:
        return []

    desc_lower = icon_description.lower()
    matched_names = [
        name for name in templates
        if name in desc_lower or desc_lower in name
    ]
    if not matched_names:
        return []

    w, h = img_size
    screen_gray = _screen_to_gray(screenshot_b64, img_size)

    candidates: list[dict] = []
    for name in matched_names:
        for tmpl in templates[name]:
            th, tw = tmpl.shape[:2]
            if th > h or tw > w:
                continue
            result = cv2.matchTemplate(screen_gray, tmpl, cv2.TM_CCOEFF_NORMED)
            locs = np.where(result >= _MATCH_THRESHOLD)
            for y_top, x_left in zip(*locs):
                x1, y1 = int(x_left), int(y_top)
                x2, y2 = x1 + tw, y1 + th
                cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                score = float(result[y_top, x_left])
                candidates.append({
                    "bbox_px": [x1, y1, x2, y2],
                    "center_px": [cx, cy],
                    "source": "template",
                    "raw_text": name,
                    "scores": {"icon": score},
                })

    return _nms(candidates)
