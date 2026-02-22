from __future__ import annotations

import asyncio
import base64
import io
from typing import Any

import numpy as np
from PIL import Image

_MAX_WIDTH = 1280


def _decode_image(screenshot_b64: str) -> np.ndarray:
    """Decode base64 PNG → numpy RGB array, downscaled to _MAX_WIDTH if wider."""
    img_bytes = base64.b64decode(screenshot_b64)
    pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = pil_img.size
    if w > _MAX_WIDTH:
        scale = _MAX_WIDTH / w
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return np.array(pil_img)


_ocr_instance: Any = None


def _get_ocr() -> Any:
    """Lazy-initialize EasyOCR reader singleton (English)."""
    global _ocr_instance
    if _ocr_instance is None:
        import easyocr  # type: ignore
        _ocr_instance = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _ocr_instance


def run_ocr_sync(screenshot_b64: str) -> tuple[list[dict], tuple[int, int]]:
    """
    Run OCR synchronously on the (downscaled) screenshot.

    Returns:
        (candidates, (img_w, img_h)) where each candidate is:
        {"bbox_px": [x1,y1,x2,y2], "center_px": [cx,cy],
         "source": "ocr", "raw_text": str, "scores": {}}
        img_w / img_h are the dimensions of the downscaled image used for OCR.
    """
    img = _decode_image(screenshot_b64)
    h, w = img.shape[:2]

    reader = _get_ocr()
    # EasyOCR returns list of (bbox, text, confidence)
    # bbox = [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
    result = reader.readtext(img, detail=1, paragraph=False)

    candidates: list[dict] = []
    for (bbox, text, _conf) in result:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        candidates.append({
            "bbox_px": [x1, y1, x2, y2],
            "center_px": [cx, cy],
            "source": "ocr",
            "raw_text": text,
            "scores": {},
        })

    return candidates, (w, h)


async def run_ocr(screenshot_b64: str) -> tuple[list[dict], tuple[int, int]]:
    """Async wrapper: runs OCR in a thread-pool executor to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_ocr_sync, screenshot_b64)
