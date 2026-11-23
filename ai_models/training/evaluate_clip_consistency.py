"""Measures how well CLIP separates matching from non-matching image-caption pairs, and derives the two thresholds the
application uses to call a pair consistent, inconsistent or unclear.

READ THIS BEFORE USING THE NUMBERS. The data is Flickr30k (everyday photos with human captions), NOT news. The
non-matching pairs are made by moving a caption to another image: "random" pairs are easy; "hard" pairs use the caption
most similar (by CLIP text embedding) to the true one, so they are closer to a plausible mix-up. Real out-of-context news
images are harder still, and NewsCLIPpings was not available here. So the result shows that the similarity carries
signal about image-text agreement, and nothing about performance on news.

The sample is split in half: thresholds are chosen on one half and reported on the other.
Usage: python ai_models/training/evaluate_clip_consistency.py [n_images]"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.multimodal.clip_consistency import DEFAULT_MODEL, ClipConsistency  # noqa: E402

URL = "https://huggingface.co/api/datasets/nlphuji/flickr_1k_test_image_text_retrieval/parquet/TEST/test/0.parquet"
RAW = ROOT / "datasets" / "raw" / "flickr1k" / "test.parquet"
SEED = 42
TARGET_PRECISION = 0.95


def thresholds(pos: np.ndarray, neg: np.ndarray) -> dict[str, float]:
    """consistent_min: lowest score from which >= 95% of pairs are matches. inconsistent_max: highest score up to which >= 95% are mismatches. Equal weight to both classes."""
    scores = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    order = np.argsort(scores)
    s, y = scores[order], y[order]
    cmin, imax = float(s.max()) + 1e-6, float(s.min()) - 1e-6
    for i in range(len(s)):  # smallest t whose upper tail has precision >= target (with a minimum tail size)
        tail = y[i:]
        if len(tail) >= 20 and tail.mean() >= TARGET_PRECISION:
            cmin = float(s[i])
            break
    for i in range(len(s) - 1, -1, -1):
        head = y[:i + 1]
        if len(head) >= 20 and (1 - head.mean()) >= TARGET_PRECISION:
            imax = float(s[i])
            break
    return {"consistent_min": round(cmin, 4), "inconsistent_max": round(imax, 4)}


def share(sim: np.ndarray, cal: dict[str, float]) -> dict[str, float]:
    return {"consistent": round(float((sim >= cal["consistent_min"]).mean()), 4),
            "inconsistent": round(float((sim <= cal["inconsistent_max"]).mean()), 4),
            "unclear": round(float(((sim > cal["inconsistent_max"]) & (sim < cal["consistent_min"])).mean()), 4)}


def main(n: int = 600) -> None:
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_bytes(urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "ddn-eval"}), timeout=300).read())  # noqa: S310
    df = pd.read_parquet(RAW).sample(n, random_state=SEED).reset_index(drop=True)
    clip = ClipConsistency(DEFAULT_MODEL)
    if not clip.available:
        raise SystemExit(clip.problem())
    captions = [str(c[0]) for c in df.caption]
    images = [Image.open(io.BytesIO(b["bytes"])).convert("RGB") for b in df.image]
    ie = np.concatenate([clip.embed_images(images[i:i + 32]).numpy() for i in range(0, n, 32)])
    te = np.concatenate([clip.embed_texts(captions[i:i + 64]).numpy() for i in range(0, n, 64)])
    sim = ie @ te.T
    matched = np.diag(sim).copy()
    rng = np.random.default_rng(SEED)
    perm = rng.permutation(n)
    while (perm == np.arange(n)).any():  # a derangement: no caption stays with its own image
        perm = rng.permutation(n)
    random_neg = sim[np.arange(n), perm]
    tt = te @ te.T
    np.fill_diagonal(tt, -1)
    hard_idx = tt.argmax(axis=1)  # for image i: the caption most similar to its own caption, from another image
    hard_neg = sim[np.arange(n), hard_idx]
    half = n // 2
    cal_idx, test_idx = np.arange(half), np.arange(half, n)
    neg_pool = lambda idx: np.concatenate([random_neg[idx], hard_neg[idx]])  # noqa: E731
    cal = thresholds(matched[cal_idx], neg_pool(cal_idx))
    cal["target_precision"] = TARGET_PRECISION
    res = {
        "model": DEFAULT_MODEL, "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": SEED,
        "what_was_measured": "Matched vs moved captions on Flickr30k test images. NOT news data; see the module docstring.",
        "n_images": n, "calibration_half": half, "held_out_half": n - half,
        "roc_auc_held_out": {
            "matched_vs_random_caption": round(float(roc_auc_score(np.r_[np.ones(len(test_idx)), np.zeros(len(test_idx))], np.r_[matched[test_idx], random_neg[test_idx]])), 4),
            "matched_vs_hard_caption": round(float(roc_auc_score(np.r_[np.ones(len(test_idx)), np.zeros(len(test_idx))], np.r_[matched[test_idx], hard_neg[test_idx]])), 4),
        },
        "mean_similarity": {"matched": round(float(matched.mean()), 4), "random_mismatch": round(float(random_neg.mean()), 4), "hard_mismatch": round(float(hard_neg.mean()), 4)},
        "thresholds": cal,
        "held_out_label_shares": {"matched": share(matched[test_idx], cal), "random_mismatch": share(random_neg[test_idx], cal), "hard_mismatch": share(hard_neg[test_idx], cal)},
        "interpretation": ("Similarity separates a caption written for an image from one moved to another image well above chance; the gap is smaller for "
                           "captions that resemble the true one. Most pairs land in 'unclear' by design (the thresholds demand 95% precision). "
                           "These are everyday photos; real news out-of-context pairs are harder and were not tested."),
    }
    (ROOT / "ai_models" / "evaluation" / "results" / "multimodal_clip_flickr.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    manifest = {"name": "flickr30k_test_1k", "source": "https://huggingface.co/datasets/nlphuji/flickr_1k_test_image_text_retrieval",
                "paper": "Young et al., From image descriptions to visual denotations (TACL 2014)", "license": "Flickr30k terms: research use only",
                "file_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(), "rows": 1000, "rows_used": n, "sampling": f"{n} images, seed {SEED}, first caption of each"}
    (ROOT / "datasets" / "manifests" / "flickr30k_test_1k.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    reg = {"module": "multimodal", "name": "text_image_consistency", "version": "1.0.0", "status": "pretrained", "language": "en",
           "algorithm": f"CLIP image-text cosine similarity ({DEFAULT_MODEL}, pretrained, not trained here) with measured thresholds and a fixed fusion rule",
           "dataset": {"name": "flickr30k_test_1k", "version": "test", "rows_clean": {"evaluated": n}},
           "calibration": cal, "metrics": {"flickr": {k: res[k] for k in ("roc_auc_held_out", "mean_similarity", "held_out_label_shares")}}}
    (ROOT / "ai_models" / "model_registry" / "multimodal_clip.json").write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("roc_auc_held_out", "mean_similarity", "thresholds", "held_out_label_shares")}, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 600)
