"""Model status registry: the single honest source for what is installed, trained and available.

Status vocabulary
  trained_baseline  trained in this project on a documented dataset, with measured metrics
  pretrained        a third-party pretrained model, used as is
  heuristic         a rule-based / signal-processing check, not a learned classifier
  experimental      works but is not validated
  unavailable       the module exists in the design but cannot run in this installation
  planned           not implemented yet
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, get_settings
from app.ml.text_detection.service import get_detector, get_urdu_detector
from app.models import DatasetVersion, ModelVersion

REGISTRY_DIR = PROJECT_ROOT / "ai_models" / "model_registry"
DATASET_SOURCES = {"gonzaloa_fake_news": "https://huggingface.co/datasets/GonzaloA/fake_news",
                   "urdu_fake_news": "https://huggingface.co/datasets/community-datasets/urdu_fake_news"}

# Modules without a trained or implemented model. They are listed so the interface can say so honestly.
STATIC_MODULES: list[dict[str, Any]] = [
    {"module": "image", "name": "ela_forensics", "version": "1.0.0", "status": "heuristic",
     "algorithm": "Error level analysis and metadata checks",
     "description": "Error Level Analysis and metadata observations. Indicators only: it does not decide whether an "
                    "image is AI-generated or manipulated."},
]


def _text_entry() -> dict[str, Any]:
    path = REGISTRY_DIR / "text_baseline_en.json"
    if get_detector().available and path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data["description"] = ("English TF-IDF + Logistic Regression baseline trained on full-length news articles. "
                               "Scores writing-pattern similarity; it does not verify facts.")
        data["limitations"] = [
            "Trained on English articles only; Urdu and other languages are declined.",
            "Needs full-length text; short claims are declined.",
            "Performance on a different dataset type (LIAR2) is much lower than on its own test split; see metrics.",
            "Does not check facts or sources and never outputs 'Misleading'.",
        ]
        return data
    return {"module": "text", "name": "text_baseline_en", "version": "1.0.0", "status": "unavailable",
            "description": get_detector().problem() or "The text model is not available.", "limitations": []}


def _urdu_entry() -> dict[str, Any]:
    path = REGISTRY_DIR / "text_baseline_ur.json"
    det = get_urdu_detector()
    if det.available and path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        data["description"] = ("Urdu baseline trained on 634 articles of one small collection (Bend the Truth). "
                               "Experimental: there is no second Urdu dataset to test it against, so how it behaves on "
                               "other Urdu news is unknown. It scores writing patterns and does not verify facts.")
        data["limitations"] = [
            "Trained on one collection of about 900 Urdu articles in five domains; no external test was possible.",
            "In its training data almost every fake article has a near-identical real partner, which is unlike real news.",
            "Roman Urdu and other Arabic-script languages are not covered.",
            "Needs full-length text. Does not check facts or sources.",
        ]
        return data
    return {"module": "text_ur", "name": "text_baseline_ur", "version": "1.0.0", "status": "unavailable",
            "description": det.problem() or "The Urdu text model is not available.", "limitations": []}


def _url_entry() -> dict[str, Any]:
    from app.ml.url_analysis.source import directory

    d = directory()
    enabled = get_settings().url_fetch_enabled
    return {
        "module": "url", "name": "url_source_checks", "version": d["version"],
        "status": "heuristic" if enabled else "unavailable",
        "algorithm": "Safe page fetch, article text extraction, the text model, and a small directory of recognised websites",
        "description": ("Reads one news page from its address, extracts the article text, runs the text model on it and "
                        "describes the website from a small hand-made directory. The two results are shown side by side and "
                        "are never merged into a score. An unfamiliar website is reported as 'not enough information', never as fake."
                        if enabled else "Reading web addresses is switched off on this server (URL_FETCH_ENABLED=false)."),
        "limitations": [
            f"The directory has {len(d['entries'])} entries. Not being listed says nothing about a website.",
            "Text is extracted without running JavaScript; pages that need it, or a login or subscription, cannot be read.",
            "No domain-age, ownership or fact-checker ratings are consulted.",
            "The writing-style result inherits every limit of the text model.",
        ],
    }


def _evidence_entry() -> dict[str, Any]:
    from app.ml.fact_checking.nli import deps_installed

    st = get_settings()
    path = REGISTRY_DIR / "evidence_nli.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not st.evidence_enabled:
        return {"module": "evidence", "name": "evidence_nli", "version": "1.0.0", "status": "unavailable",
                "description": "Evidence checking is switched off on this server (EVIDENCE_ENABLED=false).", "limitations": []}
    stance = deps_installed()
    keyed = bool(st.google_fact_check_api_key)
    data.update({
        "module": "evidence", "name": "evidence_nli", "version": data.get("version", "1.0.0"),
        "status": "pretrained" if stance else "heuristic",
        "algorithm": "Claim extraction, Wikipedia and fact-check retrieval, and natural-language inference",
        "description": ("Picks checkable claims, retrieves evidence from Wikipedia" + (" and published fact-checks" if keyed else "")
                        + (", and judges with a pretrained inference model whether each passage supports or contradicts the claim. "
                           if stance else ". The inference packages are not installed, so evidence is listed but its stance is not judged. ")
                        + "Insufficient Evidence is the default; evidence is never invented."),
        "limitations": [
            "Wikipedia is an encyclopedia: recent events and local news are often missing, which gives Insufficient Evidence.",
            "Published fact-checks are searched only when GOOGLE_FACT_CHECK_API_KEY is set" + (" (it is set)." if keyed else " (it is not set here)."),
            "The inference model compares two short texts. It cannot tell whether the evidence is itself correct.",
            "It can still call a true claim Contradicted when a page about a neighbouring subject is read as contradicting it (2 of 20 true claims in a held-out set of short, well-known claims). Open the sources.",
            "English only. Retrieval needs internet access from the server.",
        ],
    })
    return data


def _multimodal_entry() -> dict[str, Any]:
    from app.ml.multimodal.clip_consistency import REGISTRY_FILE, deps_installed, load_calibration

    data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8")) if REGISTRY_FILE.exists() else {}
    clip = deps_installed()
    calibrated = load_calibration() is not None
    data.update({
        "module": "multimodal", "name": "text_image_consistency", "version": data.get("version", "1.0.0"),
        "status": "pretrained" if clip and calibrated else "heuristic",
        "algorithm": "Text model + ELA forensics + CLIP image-text similarity, combined by a fixed written rule",
        "description": ("Analyses an image and its text together. The text model, the image forensics and a CLIP consistency check each give a "
                        "separate result, and a fixed rule (shown in every result) combines them. "
                        + ("" if clip and calibrated else "The CLIP consistency check is not available here, so only the text result and "
                           "image indicators are given. ")
                        + "Any input may be left out; missing parts are reported as missing."),
        "limitations": [
            "The combination is a hand-written rule, not a learned model: no labelled multimodal news data was available.",
            "CLIP thresholds were measured on Flickr30k photos, not news; about 1 in 10 matching captions is flagged as a mismatch.",
            "CLIP reads at most 77 tokens, so long texts are represented by their headline or opening.",
            "A mismatch or a match says nothing about whether a photo is from the event the text describes.",
            "Image forensics are indicators only and never change the verdict.",
        ],
    })
    return data


def _video_entry() -> dict[str, Any]:
    from app.ml.video_detection import faces, frames
    from app.ml.video_detection.classifier import deps_installed
    from app.ml.video_detection.pipeline import REGISTRY_FILE, calibration

    data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8")) if REGISTRY_FILE.exists() else {}
    basics = frames.cv2_installed() and faces.problem() is None
    classifier = basics and deps_installed() and calibration() is not None
    data.update({
        "module": "video", "name": data.get("name", "video_frame_swin_ffpp"), "version": data.get("version", "1.0.0"),
        "status": "experimental" if classifier else ("heuristic" if basics else "unavailable"),
        "algorithm": data.get("algorithm", "Frame sampling, face detection, per-frame measurements"),
        "description": (
            "Samples frames across the video, finds the face in each, and scores each face with an image classifier; the scores are then "
            "summarised over time. This is a frame-based classifier with temporal aggregation. It is NOT a model that learns motion or "
            "timing. " + ("" if classifier else "The classifier is not available here (needs torch, transformers and the installed "
                          "calibration), so only measurements are given: sampled frames, face boxes, sharpness and error level, with no verdict.")),
        "limitations": [
            "Frame-based: every frame is judged alone; nothing learns motion, lip-sync or flicker over time.",
            "Trained by a third party on FaceForensics++ face swaps; this project did not train it and its model card is nearly empty.",
            "Measured only on small samples (tens of videos); the intervals in the evaluation are wide.",
            "Thresholds were set on Celeb-DF; on other footage the scores shift and many videos fall in the undecided range.",
            "Needs a clear, roughly frontal face in at least 8 sampled frames; videos without faces get no verdict.",
            "Not tested on news broadcast footage, heavy re-compression, or newer generators (diffusion, lip-sync, voice clones).",
            "Audio is not analysed.",
        ]})
    return data


def list_models() -> list[dict[str, Any]]:
    return [_text_entry(), _urdu_entry(), _url_entry(), _evidence_entry(), _multimodal_entry(), _video_entry(), *[dict(m) for m in STATIC_MODULES]]


def get_video_limitations() -> str:
    m = (_video_entry().get("metrics") or {}).get("results") or {}
    fresh, test = m.get("fresh") or {}, m.get("test") or {}
    parts = ["This is a frame-based baseline: each frame is scored alone and the scores are summarised over the video. It does not detect motion or timing "
             "problems, does not analyse audio, and does not say whether the footage is used truthfully."]
    if fresh:
        ci = fresh.get("video_auc_ci95")
        parts.append(f"On a different dataset (Google DeepFakeDetection, {fresh['n_fake'] + fresh['n_real']} videos) it reached ROC-AUC {fresh.get('video_auc')}"
                     + (f" (95% interval {ci[0]} to {ci[1]})" if ci else "") + " with thresholds set on Celeb-DF; 0.5 is chance.")
    if test:
        parts.append(f"On held-out Celeb-DF videos ({test['n_fake'] + test['n_real']} videos) ROC-AUC was {test.get('video_auc')}, but that sample is optimistic.")
    parts.append("Expect weaker and less certain results on news footage, compressed or low-resolution video, and newer manipulation methods.")
    return " ".join(parts)


def get_text_limitations(language: str = "en") -> str:
    if language == "ur":
        entry = _urdu_entry()
        m = entry.get("metrics") or {}
        test = m.get("test") or {}
        return ("This is an experimental Urdu writing-pattern baseline, not a fact checker. It was trained on one small "
                f"collection and reached ROC-AUC {test.get('roc_auc')} on that collection's test split. No other Urdu "
                "data was available to test it, so its behaviour on news from other sources is unknown. "
                "Always check important claims against reliable sources.")
    entry = _text_entry()
    m = entry.get("metrics") or {}
    ext = m.get("external_liar2") or {}
    test = m.get("test") or {}
    parts = [
        "This is a writing-pattern baseline, not a fact checker. A verdict does not say whether the claims are true.",
    ]
    if test and ext:
        parts.append(
            f"On its own held-out test split it reached ROC-AUC {test.get('roc_auc')}, but on a different kind of data "
            f"(LIAR2 short political claims) ROC-AUC was only {ext.get('roc_auc')} (0.5 is chance). Expect weak "
            "results on text unlike the training articles."
        )
    parts.append("Always check important claims against reliable sources.")
    return " ".join(parts)


def sync_registry(db: Session) -> None:
    """Mirror the registry into the database so each analysis can reference the exact model version used."""
    for entry in list_models():
        if entry["status"] in ("planned", "unavailable"):
            continue
        dataset_id = None
        ds = entry.get("dataset")
        if ds:
            row = db.query(DatasetVersion).filter_by(name=ds["name"], version=ds["version"]).one_or_none()
            if row is None:
                row = DatasetVersion(name=ds["name"], version=ds["version"], language=entry.get("language"),
                                     num_samples=sum((ds.get("rows_clean") or {}).values()) or None,
                                     label_distribution=ds.get("fake_share"),
                                     source=DATASET_SOURCES.get(ds["name"]))
                db.add(row)
                db.flush()
            dataset_id = row.id
        mv = db.query(ModelVersion).filter_by(module=entry["module"], name=entry["name"], version=entry["version"]).one_or_none()
        if mv is None:
            db.add(ModelVersion(module=entry["module"], name=entry["name"], version=entry["version"], status=entry["status"],
                                artifact_path=entry.get("artifact"), metrics=entry.get("metrics"), dataset_version_id=dataset_id))
        else:
            mv.status, mv.metrics, mv.dataset_version_id = entry["status"], entry.get("metrics"), dataset_id
    db.commit()


def model_version_id(db: Session, module: str) -> int | None:
    mv = db.query(ModelVersion).filter_by(module=module, is_active=True).order_by(ModelVersion.id.desc()).first()
    return mv.id if mv else None
