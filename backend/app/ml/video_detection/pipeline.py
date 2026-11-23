"""The whole video analysis: validate, sample frames, find faces, score them, summarise over time, decide.

Result honesty rules built in here:
- a video is never judged from one frame (at least temporal.MIN_FACE_FRAMES frames with a face are needed);
- a frame without a detected face is reported as such and not scored;
- the verdict comes only from a classifier whose decision thresholds were measured (registry file); without them the
  per-frame scores are shown but not interpreted;
- the classifier looks at each frame alone. The temporal part is a summary of the frame scores, not a temporal model."""
from __future__ import annotations

import io
import json
import threading
from typing import Any

import numpy as np

from app.core.config import PROJECT_ROOT
from app.ml.video_detection import faces, temporal
from app.ml.video_detection import frames as vf
from app.ml.video_detection.classifier import FrameClassifier, get_classifier

REGISTRY_FILE = PROJECT_ROOT / "ai_models" / "model_registry" / "video_frame.json"
THUMB_SIDE = 320
FRAME_VERDICT_NOTE = ("Each frame was scored on its own by an image classifier. The summary over time (average level, share of flagged frames, "
                      "longest run) describes those scores; it is not a model that learns motion or timing.")
_slots = threading.BoundedSemaphore(2)  # videos analysed at the same time on this server


class Busy(RuntimeError):
    pass


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_FILE.read_text(encoding="utf-8")) if REGISTRY_FILE.exists() else {}


def calibration() -> dict[str, Any] | None:
    cal = (load_registry().get("metrics") or {}).get("calibration")
    aggregator = (load_registry().get("metrics") or {}).get("aggregator")
    if not cal or aggregator not in temporal.AGGREGATORS:
        return None
    return {**cal, "aggregator": aggregator}


def _thumbnail(frame_bgr: np.ndarray, box: tuple[int, int, int, int] | None) -> bytes:
    import cv2

    h, w = frame_bgr.shape[:2]
    scale = min(1.0, THUMB_SIDE / max(h, w))
    img = cv2.resize(frame_bgr, (max(1, int(w * scale)), max(1, int(h * scale)))) if scale < 1.0 else frame_bgr.copy()
    if box is not None:
        x, y, bw, bh = (int(v * scale) for v in box)
        cv2.rectangle(img, (x, y), (x + bw, y + bh), (255, 160, 0), 2)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return buf.tobytes() if ok else b""


def _sharpness(crop_rgb: np.ndarray) -> float:
    import cv2

    return round(float(cv2.Laplacian(cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY), cv2.CV_64F).var()), 2)


def _ela_mean(crop_rgb: np.ndarray) -> float | None:
    """Error level of the face crop, the same measurement the image module makes. An indicator, never a verdict."""
    from PIL import Image

    from app.ml.image_detection import ela

    buf = io.BytesIO()
    Image.fromarray(crop_rgb).save(buf, format="JPEG", quality=95)
    try:
        return ela.analyse(buf.getvalue(), 4_000_000).ela_mean
    except ela.ImageRejected:
        return None


def unavailable_reason(classifier: FrameClassifier | None = None) -> str | None:
    """Why video analysis cannot run at all. A missing classifier is NOT a reason: frames and indicators still work."""
    if not vf.cv2_installed():
        return "The package opencv-python-headless is not installed (pip install -r backend/requirements-ml.txt)."
    return faces.problem()


def analyse(data: bytes, max_seconds: int, n_frames: int, classifier: FrameClassifier | None = None) -> tuple[dict[str, Any], vf.VideoInfo, list[bytes], str]:
    """Returns (details, video info, one JPEG thumbnail per sampled frame in order, verdict)."""
    if not _slots.acquire(blocking=False):
        raise Busy("Other videos are being analysed right now. Try again in a minute.")
    try:
        return _analyse(data, max_seconds, n_frames, classifier)
    finally:
        _slots.release()


def _analyse(data, max_seconds, n_frames, classifier):
    reason = unavailable_reason(classifier)
    if reason:
        raise RuntimeError(reason)
    ext = vf.sniff_extension(data[:16])
    clf = classifier if classifier is not None else get_classifier()
    clf_problem = clf.problem()
    cal = calibration()
    frames_out: list[dict[str, Any]] = []
    thumbs: list[bytes] = []
    crops: list[np.ndarray] = []
    crop_pos: list[int] = []
    with vf.temp_video(data, ext) as path:
        info = vf.probe(path, ext, max_seconds)
        for fr in vf.read_frames(path, info, n_frames):
            face = faces.largest_face(fr.image)
            entry: dict[str, Any] = {"index": fr.index, "t": fr.timestamp, "face_found": face is not None, "face_size": None,
                                     "p_fake": None, "sharpness": None, "ela_mean": None, "thumbnail": len(thumbs)}
            if face is not None:
                entry.update(face_size=face.relative_size, sharpness=_sharpness(face.crop), ela_mean=_ela_mean(face.crop))
                crops.append(face.crop)
                crop_pos.append(len(frames_out))
            thumbs.append(_thumbnail(fr.image, face.box if face else None))
            frames_out.append(entry)
    if not frames_out:
        raise vf.VideoRejected("No frames could be read from the video.")
    scores: list[float] = []
    if crops and clf_problem is None:
        scores = clf.p_fake(crops)
        for pos, p in zip(crop_pos, scores):
            frames_out[pos]["p_fake"] = p
    with_face = len(crops)
    times = [frames_out[i]["t"] for i in crop_pos]

    observations: list[str] = []
    temporal_part: dict[str, Any] | None = None
    thresholds = {k: cal[k] for k in ("fake_min", "real_max", "target_precision")} if cal else None
    status, verdict = "classifier_unavailable", "Indicators Only"
    if with_face < temporal.MIN_FACE_FRAMES:
        status, verdict = "not_enough_faces", "Unverified"
        observations.append(f"A clear face was found in {with_face} of {len(frames_out)} sampled frames; at least {temporal.MIN_FACE_FRAMES} are needed, "
                            "so no call is made. A video is never judged from a single frame.")
    elif clf_problem is not None:
        observations.append("The frame classifier is not available here, so only measurements are given: sampled frames, face boxes, sharpness and error level.")
    else:
        agg_name = (cal or {}).get("aggregator") or "mean"
        agg = temporal.aggregate(scores)
        temporal_part = {**temporal.summarise(times, scores), "aggregator": agg_name, "video_score": round(agg[agg_name], 4),
                         "suspicious_moments": temporal.suspicious_moments(times, scores)}
        if cal is None:
            status, verdict = "not_calibrated", "Indicators Only"
            observations.append("No measured decision thresholds are installed for this classifier, so the scores are shown without a verdict.")
        else:
            call = temporal.decide(agg[agg_name], cal)
            if call == "fake":
                status, verdict = "decided", "Likely Fake"
            elif call == "real":
                status, verdict = "decided", "Likely Real"
            else:
                status, verdict = "undecided", "Unverified"
                observations.append("The overall score is in the range where this classifier was not reliable, so no call is made.")
            if thresholds and (thresholds["fake_min"] is None or thresholds["real_max"] is None):
                missing = "fake" if thresholds["fake_min"] is None else "real"
                observations.append(f"On the test videos this classifier never reached {int(temporal.TARGET_PRECISION * 100)}% precision for a '{missing}' call, so it makes none.")
    rule = ("Frames are sampled evenly across the video and the largest face in each is scored by an image classifier. "
            f"The video score is the {(cal or {}).get('aggregator', 'mean')} of the face-frame scores. At least {temporal.MIN_FACE_FRAMES} frames with a face are required. "
            "Scores above the 'fake' threshold give Likely Fake, scores below the 'real' threshold give Likely Real, anything between gives Unverified. "
            "The thresholds were measured on training videos (see Models).")
    details = {
        "video": {"width": info.width, "height": info.height, "fps": info.fps, "frame_count": info.frame_count,
                  "duration_seconds": info.duration_seconds, "container": info.extension},
        "sampling": {"requested": n_frames, "sampled": len(frames_out), "with_face": with_face, "min_face_frames": temporal.MIN_FACE_FRAMES},
        "frames": frames_out,
        "temporal": temporal_part,
        "decision": {"status": status, "rule": rule, "thresholds": thresholds},
        "model": {"kind": "frame_based_classifier_with_temporal_aggregation", "id": clf.model_id if clf_problem is None else None,
                  "temporal_model": False, "note": FRAME_VERDICT_NOTE, "problem": clf_problem},
        "observations": observations,
    }
    return details, info, thumbs, verdict
