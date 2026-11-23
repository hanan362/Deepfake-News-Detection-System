"""Measures a pretrained frame-based deepfake classifier on videos, and calibrates the video decision rule.

The model: a Swin-Tiny fine-tuned by a third party on FaceForensics++ face crops (hchcsuim/FFPP-Raw_1FPS_faces-expand-40-
aligned_val-ds-celeb-df, Apache-2.0). Its model card is nearly empty; the repository name says Celeb-DF was used as the
validation set. This project did not train it.

Three sets of videos are used, with different jobs:
  calibration  120 Celeb-DF v2 videos that are NOT on the official test list. The way frame scores are combined and the
               two decision thresholds are chosen here, and only here.
  test         48 videos from the official Celeb-DF v2 test list. Reported, never tuned on. BUT: this model was picked
               from five candidates by looking at the first 24+24 videos of this sample, and the model's own validation
               set may overlap with Celeb-DF, so these numbers are optimistic.
  fresh        40 videos from Google's DeepFakeDetection set (a different dataset, different actors, different method),
               scored once with the thresholds from the calibration set. This is the closest thing here to an honest
               cross-dataset number.
All three are small seeded samples; each result carries a bootstrap 95% interval over videos so the uncertainty is visible.

Usage: python ai_models/training/evaluate_video.py [--frames N] [--write-registry]"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.video_detection import faces, temporal  # noqa: E402
from app.ml.video_detection import frames as vf  # noqa: E402
from app.ml.video_detection.classifier import DEFAULT_MODEL, DEFAULT_REVISION, FrameClassifier  # noqa: E402

RAW = ROOT / "datasets" / "raw"
SETS = {"calibration": "celebdf_v2_train", "test": "celebdf_v2_test", "fresh": "dfd_sample"}
CACHE = ROOT / "ai_models" / "evaluation" / "cache"
SEED = 42


def score_video(path: Path, clf: FrameClassifier, n_frames: int) -> dict:
    data = path.read_bytes()
    info = vf.probe(path, vf.sniff_extension(data[:16]), max_seconds=600, max_side=8192)
    crops, meta, sampled = [], [], 0
    for fr in vf.read_frames(path, info, n_frames):
        sampled += 1
        face = faces.largest_face(fr.image)
        if face is not None:
            crops.append(face.crop)
            meta.append({"index": fr.index, "t": fr.timestamp, "face_size": face.relative_size})
    scores = clf.p_fake(crops) if crops else []
    return {"sampled": sampled, "duration": info.duration_seconds, "frames": [{**m, "p_fake": p} for m, p in zip(meta, scores)]}


def score_set(name: str, clf: FrameClassifier, n_frames: int) -> dict:
    folder = RAW / SETS[name]
    rows = [l.split("\t") for l in (folder / "selected.txt").read_text().splitlines() if l.strip()]
    tag = hashlib.sha1(f"{clf.model_id}|{clf.revision}|{n_frames}|{faces.CROP_MARGIN}|{faces.SCORE_THRESHOLD}".encode()).hexdigest()[:8]
    cache_file = CACHE / f"video_{name}_{tag}.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    for i, (label, rel) in enumerate(rows):
        path = folder / rel.replace("/", "__")
        if rel in cache or not path.exists():
            continue
        try:
            cache[rel] = {"label": label, **score_video(path, clf, n_frames)}
        except vf.VideoRejected as exc:
            cache[rel] = {"label": label, "error": str(exc), "frames": [], "sampled": 0}
        cache_file.write_text(json.dumps(cache))
        print(f"[{name}] {i + 1}/{len(rows)} {rel} faces={len(cache[rel]['frames'])}", flush=True)
    return cache


def auc(y, s):
    y = np.asarray(y)
    return round(float(roc_auc_score(y, s)), 4) if len(set(y.tolist())) == 2 else None


def bootstrap_ci(y, s, n=1000, seed=SEED):
    rng = np.random.default_rng(seed)
    y, s = np.asarray(y), np.asarray(s)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i].tolist())) == 2:
            vals.append(roc_auc_score(y[i], s[i]))
    return [round(float(np.percentile(vals, 2.5)), 3), round(float(np.percentile(vals, 97.5)), 3)] if vals else None


def prepare(cache: dict):
    usable = {rel: v for rel, v in cache.items() if "error" not in v and len(v["frames"]) >= temporal.MIN_FACE_FRAMES}
    y = np.array([1 if v["label"] == "fake" else 0 for v in usable.values()])
    probs = [[f["p_fake"] for f in v["frames"]] for v in usable.values()]
    return usable, y, probs


def video_level(y, probs, agg):
    return np.array([temporal.aggregate(p)[agg] for p in probs])


def evaluate(name: str, cache: dict, cal: dict, agg: str) -> dict:
    usable, y, probs = prepare(cache)
    s = video_level(y, probs, agg)
    fr_y = np.array([1 if v["label"] == "fake" else 0 for v in usable.values() for _ in v["frames"]])
    fr_s = np.array([p for ps in probs for p in ps])
    return {"videos_read": len(cache), "videos_used": len(usable), "videos_unusable": len(cache) - len(usable),
            "n_fake": int(y.sum()), "n_real": int(len(y) - y.sum()), "face_frames": int(len(fr_y)),
            "frame_auc": auc(fr_y, fr_s), "video_auc": auc(y, s), "video_auc_ci95": bootstrap_ci(y, s),
            "video_auc_by_aggregator": {a: auc(y, video_level(y, probs, a)) for a in temporal.AGGREGATORS},
            "single_frame_auc": auc(y, np.array([p[0] for p in probs])),
            "constant_answer_accuracy": round(max(y.mean(), 1 - y.mean()), 4), "decision_rule": temporal.report_on(y, s, cal)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=16)
    ap.add_argument("--write-registry", action="store_true", help="write the calibration the application reads")
    args = ap.parse_args()
    clf = FrameClassifier(DEFAULT_MODEL, DEFAULT_REVISION)
    if clf.problem() or faces.problem():
        sys.exit(f"Cannot evaluate: {clf.problem() or faces.problem()}")
    t0 = time.time()
    caches = {n: score_set(n, clf, args.frames) for n in SETS if (RAW / SETS[n] / "selected.txt").exists()}
    print(f"scoring took {time.time() - t0:.0f}s")

    _, y_cal, p_cal = prepare(caches["calibration"])
    cal_auc = {a: auc(y_cal, video_level(y_cal, p_cal, a)) for a in temporal.AGGREGATORS}
    agg = max(temporal.AGGREGATORS, key=lambda a: cal_auc[a] or 0)
    cal = temporal.calibrate(y_cal, video_level(y_cal, p_cal, agg))
    results = {n: evaluate(n, caches[n], cal, agg) for n in caches}
    out = {"model": DEFAULT_MODEL, "revision": DEFAULT_REVISION, "frames_per_video": args.frames, "created_at": datetime.now(timezone.utc).isoformat(),
           "seed": SEED, "face_crop_margin": faces.CROP_MARGIN, "aggregator": agg, "calibration_auc_by_aggregator": cal_auc, "calibration": cal,
           "sets": {"calibration": "Celeb-DF v2, 60 real + 60 fake, not on the official test list",
                    "test": "Celeb-DF v2 official test list, seeded sample of 24 real + 24 fake (model was chosen while looking at part of this sample)",
                    "fresh": "Google DeepFakeDetection (angads24/deepfake-video), seeded sample of 20 real + 20 fake"},
           "results": results}
    (ROOT / "ai_models" / "evaluation" / "results").mkdir(parents=True, exist_ok=True)
    (ROOT / "ai_models" / "evaluation" / "results" / "video_frame_model.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"aggregator": agg, "calibration": cal, "calibration_auc": cal_auc}, indent=1))
    for n, r in results.items():
        print(n, json.dumps(r))
    if args.write_registry:
        reg = {"module": "video", "name": "video_frame_swin_ffpp", "version": "1.0.0", "status": "experimental",
               "algorithm": "YuNet face detection + Swin-Tiny frame classifier (third-party, fine-tuned on FaceForensics++) + aggregation of frame scores",
               "model_id": DEFAULT_MODEL, "revision": DEFAULT_REVISION, "created_at": out["created_at"], "metrics": out}
        (ROOT / "ai_models" / "model_registry").mkdir(exist_ok=True)
        (ROOT / "ai_models" / "model_registry" / "video_frame.json").write_text(json.dumps(reg, indent=2))
        print("registry written")


if __name__ == "__main__":
    main()
