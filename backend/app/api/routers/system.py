"""Health check, the public module status, and the administrator-only model details."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, get_settings
from app.api.deps import require_admin
from app.core.errors import APIError
from app.db.session import get_db
from app.ml.text_detection.service import get_detector, get_urdu_detector
from app.services.registry import list_models

router = APIRouter(tags=["system"])


@router.get("/health", summary="Service health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    s = get_settings()
    return {"status": "ok" if database == "ok" else "degraded", "version": s.app_version, "environment": s.environment,
            "database": database, "text_model": "available" if get_detector().available else "missing",
            "urdu_text_model": "available" if get_urdu_detector().available else "missing"}


# What a visitor is told about each check. These are written for readers, not taken from the model registry, whose
# descriptions name datasets and algorithms. The registry stays administrator-only.
PUBLIC_DESCRIPTION = {
    "text": "Reads the wording of an English article and shows how closely it resembles articles known to be real or fake. It does not check facts.",
    "text_ur": "Reads the wording of an Urdu article in the same way. It is experimental, so treat the result as a weak hint.",
    "url": "Reads a news page from its web address, runs the text check on it and describes the website it is on.",
    "evidence": "Looks up the claims in a text on Wikipedia and in published fact-checks, and shows what it found.",
    "multimodal": "Checks whether a picture and its caption belong together.",
    "video": "Looks at the faces in a video for signs of a face swap. It is experimental.",
    "image": "Looks for signs that a photo was edited. It shows measurements, not a verdict.",
}


@router.get("/modules", summary="Which checks are switched on, and the size limits (public, no sign-in needed)")
def modules():
    """What an ordinary visitor needs to use the checks: whether each one runs, a plain description, and the input limits.

    The model names, versions, algorithms and measured numbers are not here. They are in `GET /models`, which needs an
    administrator account."""
    s = get_settings()
    out = []
    for m in list_models():
        down = m["status"] in ("unavailable", "planned")
        out.append({"module": m["module"], "status": m["status"],
                    "description": "This check is not available on this server right now." if down else PUBLIC_DESCRIPTION.get(m["module"], "")})
    return {"models": out,
            "limits": {"min_text_words": s.min_text_tokens, "max_text_chars": s.max_text_chars,
                       "max_image_mb": s.max_image_mb, "max_image_pixels": s.max_image_pixels,
                       "max_video_mb": s.max_video_mb, "max_video_seconds": s.max_video_seconds,
                       "text_languages": ["en"] + (["ur"] if get_urdu_detector().available else [])}}


@router.get("/models", summary="Status of every analysis module and model, with the measured numbers (administrators only)",
            dependencies=[Depends(require_admin)])
def models():
    s = get_settings()
    return {"models": list_models(),
            "limits": {"min_text_words": s.min_text_tokens, "max_text_chars": s.max_text_chars,
                       "max_image_mb": s.max_image_mb, "max_image_pixels": s.max_image_pixels,
                       "max_video_mb": s.max_video_mb, "max_video_seconds": s.max_video_seconds,
                       "video_sample_frames": s.video_sample_frames, "video_min_face_frames": 8,
                       "text_confidence_threshold": s.text_confidence_threshold,
                       "text_languages": ["en"] + (["ur"] if get_urdu_detector().available else [])},
            "status_meanings": {
                "trained_baseline": "Trained in this project on a documented dataset, with measured metrics.",
                "pretrained": "A third-party pretrained model used as is.",
                "heuristic": "A rule-based or signal-processing check, not a learned classifier.",
                "experimental": "Runs but has not been validated.",
                "unavailable": "Part of the design but cannot run in this installation.",
                "planned": "Not implemented yet.",
            }}


@router.get("/models/text/evaluation", summary="Measured evaluation of the text baseline (administrators only)",
            dependencies=[Depends(require_admin)])
def text_evaluation():
    """The full comparison of the candidate models and the dataset description, exactly as written by the training run."""
    results = PROJECT_ROOT / "ai_models" / "evaluation" / "results" / "text_baseline_en_metrics.json"
    manifest = PROJECT_ROOT / "datasets" / "manifests" / "gonzaloa_fake_news.json"
    if not results.exists() or not manifest.exists():
        raise APIError(404, "NOT_FOUND", "No evaluation results yet. Run: python ai_models/training/train_text_baseline.py")
    return {"evaluation": json.loads(results.read_text(encoding="utf-8")), "dataset": json.loads(manifest.read_text(encoding="utf-8"))}


@router.get("/models/text-ur/evaluation", summary="Measured evaluation of the Urdu baseline (administrators only)",
            dependencies=[Depends(require_admin)])
def urdu_evaluation():
    results = PROJECT_ROOT / "ai_models" / "evaluation" / "results" / "text_baseline_ur_metrics.json"
    manifest = PROJECT_ROOT / "datasets" / "manifests" / "urdu_fake_news.json"
    if not results.exists() or not manifest.exists():
        raise APIError(404, "NOT_FOUND", "No Urdu evaluation results yet. Run: python ai_models/training/train_text_urdu.py")
    return {"evaluation": json.loads(results.read_text(encoding="utf-8")), "dataset": json.loads(manifest.read_text(encoding="utf-8"))}


@router.get("/models/evidence/evaluation", summary="Measured evaluation of the evidence stance model (administrators only)",
            dependencies=[Depends(require_admin)])
def evidence_evaluation():
    results = PROJECT_ROOT / "ai_models" / "evaluation" / "results" / "evidence_nli_fever.json"
    manifest = PROJECT_ROOT / "datasets" / "manifests" / "fever_gold_evidence.json"
    if not results.exists() or not manifest.exists():
        raise APIError(404, "NOT_FOUND", "No evidence evaluation yet. Run: python ai_models/training/evaluate_evidence_nli.py")
    return {"evaluation": json.loads(results.read_text(encoding="utf-8")), "dataset": json.loads(manifest.read_text(encoding="utf-8"))}


@router.get("/models/video/evaluation", summary="Measured evaluation of the video frame model (administrators only)",
            dependencies=[Depends(require_admin)])
def video_evaluation():
    results = PROJECT_ROOT / "ai_models" / "evaluation" / "results" / "video_frame_model.json"
    if not results.exists():
        raise APIError(404, "NOT_FOUND", "No video evaluation yet. Run: python ai_models/training/evaluate_video.py")
    return {"evaluation": json.loads(results.read_text(encoding="utf-8"))}
