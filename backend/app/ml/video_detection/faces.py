"""Finding the face to analyse in a frame with YuNet, a small face detector that ships with this project
(ai_models/checkpoints/face_detector, MIT licence, runs through OpenCV's own DNN module: no extra download).

(OpenCV 5 removed the older Haar cascade detector, so YuNet is used on every OpenCV version.)

It finds clear faces well and misses small, strongly turned, blurred or partly hidden ones. A frame without a detected
face is reported as such and skipped; it is never scored as if it were real. The largest face in the frame is used."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.config import PROJECT_ROOT

MODEL_FILE = PROJECT_ROOT / "ai_models" / "checkpoints" / "face_detector" / "face_detection_yunet_2023mar.onnx"
MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
DETECT_SIDE = 640         # frames are shrunk to this long side before detection
MIN_FACE_FRACTION = 0.08  # the face must be at least this share of the shorter frame side
SCORE_THRESHOLD = 0.8
CROP_MARGIN = 0.40        # context kept around the detected box (the frame model was trained on faces expanded by 40%)
_state: dict[str, Any] = {}


@dataclass
class Face:
    box: tuple[int, int, int, int]  # x, y, w, h in the original frame
    crop: np.ndarray                # RGB crop with margin
    relative_size: float            # face width as a share of the frame width
    confidence: float


def problem() -> str | None:
    if not MODEL_FILE.exists():
        return f"The face detector file {MODEL_FILE.name} is missing from ai_models/checkpoints/face_detector."
    if hashlib.sha256(MODEL_FILE.read_bytes()).hexdigest() != MODEL_SHA256:
        return "The face detector file does not match the expected checksum."
    return None


def _detector(size: tuple[int, int]):
    import cv2

    det = _state.get("det")
    if det is None:
        det = cv2.FaceDetectorYN.create(str(MODEL_FILE), "", size, SCORE_THRESHOLD, 0.3, 20)
        _state["det"] = det
    det.setInputSize(size)
    return det


def largest_face(frame_bgr: np.ndarray) -> Face | None:
    import cv2

    h, w = frame_bgr.shape[:2]
    scale = min(1.0, DETECT_SIDE / max(h, w))
    small = cv2.resize(frame_bgr, (max(1, int(w * scale)), max(1, int(h * scale)))) if scale < 1.0 else frame_bgr
    sh, sw = small.shape[:2]
    _, found = _detector((sw, sh)).detect(small)
    if found is None or len(found) == 0:
        return None
    best = None
    for row in found:
        x, y, fw, fh = (int(round(v / scale)) for v in row[:4])
        if fw <= 0 or fh <= 0 or fw < MIN_FACE_FRACTION * min(h, w):
            continue
        if best is None or fw * fh > best[2] * best[3]:
            best = (x, y, fw, fh, float(row[14]))
    if best is None:
        return None
    x, y, fw, fh, conf = best
    m = int(CROP_MARGIN * max(fw, fh))
    x0, y0, x1, y1 = max(0, x - m), max(0, y - m), min(w, x + fw + m), min(h, y + fh + m)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    crop = cv2.cvtColor(frame_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
    return Face((max(0, x), max(0, y), fw, fh), crop, round(fw / w, 4), round(conf, 3))
