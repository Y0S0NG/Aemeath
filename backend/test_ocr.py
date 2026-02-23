"""
Standalone OCR test script — visualises EasyOCR candidates on a screenshot.

Usage:
    # Take a fresh screenshot and annotate it:
    python test_ocr.py

    # Annotate an existing image file:
    python test_ocr.py path/to/image.png

Output:
    ocr_result.png  — annotated image with bounding boxes and detected text labels
"""

import base64
import io
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageGrab

# Allow importing from the app package without installing it
sys.path.insert(0, str(Path(__file__).parent))
from app.locator.ocr_engine import run_ocr_sync


def load_image_as_b64(image_path: str | None) -> tuple[str, np.ndarray]:
    """
    Load an image from disk, or take a macOS screenshot if no path given.
    Returns (base64_string, original_pil_image_as_numpy).
    """
    if image_path:
        pil_img = Image.open(image_path).convert("RGB")
        print(f"Loaded image: {image_path}  ({pil_img.width}×{pil_img.height})")
    else:
        print("Taking screenshot in 2 seconds — switch to the window you want to test...")
        import time; time.sleep(2)
        pil_img = ImageGrab.grab().convert("RGB")
        print(f"Screenshot captured: {pil_img.width}×{pil_img.height}")

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return b64, np.array(pil_img)


def draw_candidates(orig_img: np.ndarray, candidates: list[dict], img_size: tuple[int, int]) -> np.ndarray:
    """
    Draw bounding boxes and text labels on the original image.
    Scales bbox_px coords from the (possibly downscaled) OCR space back to orig_img space.
    """
    ocr_w, ocr_h = img_size
    orig_h, orig_w = orig_img.shape[:2]
    scale_x = orig_w / ocr_w
    scale_y = orig_h / ocr_h

    annotated = orig_img.copy()
    # BGR colour for OpenCV
    BOX_COLOR   = (50, 200, 50)    # green
    TEXT_COLOR  = (255, 255, 255)  # white
    BG_COLOR    = (50, 200, 50)    # green label background

    for c in candidates:
        x1, y1, x2, y2 = c["bbox_px"]
        # Scale back to original resolution
        x1s = int(x1 * scale_x)
        y1s = int(y1 * scale_y)
        x2s = int(x2 * scale_x)
        y2s = int(y2 * scale_y)

        # Bounding box
        cv2.rectangle(annotated, (x1s, y1s), (x2s, y2s), BOX_COLOR, 2)

        # Label: raw_text above the box
        label = c["raw_text"]
        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness  = 1
        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
        label_y = max(y1s - 4, th + 4)

        # Filled label background for readability
        cv2.rectangle(annotated,
                      (x1s, label_y - th - baseline),
                      (x1s + tw, label_y + baseline),
                      BG_COLOR, cv2.FILLED)
        cv2.putText(annotated, label, (x1s, label_y - baseline),
                    font, font_scale, TEXT_COLOR, thickness, cv2.LINE_AA)

    return annotated


def main() -> None:
    image_path = sys.argv[1] if len(sys.argv) > 1 else None

    # 1. Load / capture image
    b64, orig_np = load_image_as_b64(image_path)

    # 2. Run OCR (uses the same code path as the real backend)
    print("Running OCR…")
    candidates, img_size = run_ocr_sync(b64)

    # 3. Print summary
    print(f"\nDetected {len(candidates)} text candidates (OCR image size: {img_size[0]}×{img_size[1]}):")
    for i, c in enumerate(candidates):
        x1, y1, x2, y2 = [round(v) for v in c["bbox_px"]]
        print(f"  [{i+1:3d}] ({x1:4d},{y1:4d})→({x2:4d},{y2:4d})  \"{c['raw_text']}\"")

    # 4. Annotate and save
    orig_bgr = cv2.cvtColor(orig_np, cv2.COLOR_RGB2BGR)
    annotated_bgr = draw_candidates(orig_bgr, candidates, img_size)

    output_path = "ocr_result.png"
    cv2.imwrite(output_path, annotated_bgr)
    print(f"\nAnnotated image saved → {output_path}")

    # 5. Open immediately on macOS
    import subprocess
    subprocess.run(["open", output_path], check=False)


if __name__ == "__main__":
    main()
