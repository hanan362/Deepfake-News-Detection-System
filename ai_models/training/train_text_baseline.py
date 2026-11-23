"""Train and evaluate the English text baseline for the Deepfake News Detection System.

Everything written to disk is a real measurement from this run; nothing is hard-coded.

Stages (each one caches its output, so an interrupted run resumes instead of starting over):
  download  -> fetch GonzaloA/fake_news (training data) and LIAR2 (external test set) from Hugging Face
  prepare   -> validate, clean, de-duplicate, prevent train/validation/test leakage
  features  -> fit the TF-IDF vectoriser on the training split only
  train     -> fit + evaluate one model (--model logistic_regression|naive_bayes|linear_svm|random_forest)
  finalize  -> write the deployed checkpoint, the model-registry entry, the dataset manifest and the metrics
  all       -> run every stage in order (default)

Run from the project root:   python ai_models/training/train_text_baseline.py
Optional environment variables: DFND_RAW_DIR (where raw files are cached), DFND_WORK_DIR (intermediate files).
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.text_detection.preprocess import clean_text  # noqa: E402

RAW = Path(os.environ.get("DFND_RAW_DIR", ROOT / "datasets" / "raw"))
WORK = Path(os.environ.get("DFND_WORK_DIR", ROOT / "datasets" / "processed" / "text_en"))
MANIFESTS = ROOT / "datasets" / "manifests"
CKPT = ROOT / "ai_models" / "checkpoints" / "text_baseline_en"
REGISTRY = ROOT / "ai_models" / "model_registry"
RESULTS = ROOT / "ai_models" / "evaluation" / "results"
SEED = 42
MODEL_NAME, MODEL_VERSION = "text_baseline_en", "1.0.0"
MODELS = ["logistic_regression", "naive_bayes", "linear_svm", "random_forest"]

HF = "https://huggingface.co/datasets"
SOURCES = {
    "train": (f"{HF}/GonzaloA/fake_news/resolve/main/data/train-00000-of-00001.parquet", RAW / "gonzaloa_fake_news" / "train.parquet"),
    "validation": (f"{HF}/GonzaloA/fake_news/resolve/main/data/validation-00000-of-00001.parquet", RAW / "gonzaloa_fake_news" / "validation.parquet"),
    "test": (f"{HF}/GonzaloA/fake_news/resolve/main/data/test-00000-of-00001.parquet", RAW / "gonzaloa_fake_news" / "test.parquet"),
    "liar": (f"{HF}/chengxuphd/liar2/resolve/main/test.csv", RAW / "liar2" / "test.csv"),
}


def log(*a) -> None:
    print(*a, flush=True)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file(url: str, dest: Path, retries: int = 6) -> None:
    """Resumable, atomic download. A partial file is continued with an HTTP Range request and only renamed to its
    final name once complete, so an interrupted run never leaves a corrupt file behind."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        have = tmp.stat().st_size if tmp.exists() else 0
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-"} if have else {})
        total = 0
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resumed = have > 0 and r.status == 206
                if have and not resumed:
                    have = 0  # the server ignored the Range header: start over
                length = int(r.headers.get("Content-Length", 0))
                total = have + length if length else 0
                log(f"downloading {url} ({'resuming at %d MB' % (have >> 20) if resumed else 'from the start'})")
                with open(tmp, "ab" if resumed else "wb") as f:
                    while chunk := r.read(1 << 20):
                        f.write(chunk)
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and have:  # nothing left to fetch: the partial file is already complete
                total = have
            else:
                log(f"attempt {attempt} failed: HTTP {exc.code}")
                continue
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as exc:
            log(f"attempt {attempt} interrupted: {exc}")
            continue
        if total and tmp.stat().st_size != total:
            log(f"attempt {attempt}: incomplete ({tmp.stat().st_size} of {total} bytes)")
            continue
        tmp.replace(dest)
        return
    raise RuntimeError(f"could not download {url}")


def stage_download() -> None:
    for _, (url, dest) in SOURCES.items():
        download_file(url, dest)
        log(f"ok {dest.name}  {dest.stat().st_size / 1e6:.1f} MB")


def text_hash(s: str) -> str:
    return hashlib.sha1(" ".join(s.lower().split()).encode("utf-8")).hexdigest()


def stage_prepare() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    frames = {s: pd.read_parquet(SOURCES[s][1]) for s in ("train", "validation", "test")}
    report: dict = {"file_sha256": {s: sha256_of(SOURCES[s][1]) for s in frames},
                    "rows_raw": {k: int(len(v)) for k, v in frames.items()}}

    # Verify what label 1 means instead of trusting the dataset card: wire-agency articles are the "real" class.
    tr = frames["train"]
    rate = {int(lab): float(tr[tr["label"] == lab]["text"].str.contains(r"\(Reuters\)", regex=True).mean())
            for lab in sorted(tr["label"].unique())}
    report["reuters_tag_rate_by_label"] = rate
    if not rate[1] > rate[0]:
        raise SystemExit("unexpected label semantics - inspect the dataset before training")

    seen: set[str] = set()
    removed = {"empty_or_short": 0, "duplicates_or_cross_split_leak": 0}
    for split in ("train", "validation", "test"):  # a duplicate stays in the earliest split only
        df = frames[split].copy()
        df["title"] = df["title"].fillna("")
        df["text"] = df["text"].fillna("")
        df["raw"] = (df["title"] + ". " + df["text"]).str.strip()
        df["clean"] = df["raw"].map(clean_text)
        short = df["clean"].str.split().str.len() < 20
        removed["empty_or_short"] += int(short.sum())
        df = df[~short]
        keep = []
        for h in df["raw"].map(text_hash):
            keep.append(h not in seen)
            seen.add(h)
        removed["duplicates_or_cross_split_leak"] += int(len(keep) - sum(keep))
        df = df[keep].copy()
        df["y_fake"] = (1 - df["label"].astype(int)).astype(int)  # 1 = fake, 0 = real
        df[["clean", "y_fake"]].reset_index(drop=True).to_parquet(WORK / f"clean_{split}.parquet")
        report.setdefault("rows_clean", {})[split] = int(len(df))
        report.setdefault("label_distribution_fake_share", {})[split] = round(float(df["y_fake"].mean()), 4)
    report["removed"] = removed

    # LIAR2: 0 pants-fire, 1 false, 2 barely-true, 3 half-true, 4 mostly-true, 5 true  ->  0-2 false-ish, 3-5 true-ish
    liar = pd.read_csv(SOURCES["liar"][1]).dropna(subset=["statement"])
    liar["clean"] = liar["statement"].map(clean_text)
    liar["y_fake"] = (liar["label"].astype(int) <= 2).astype(int)
    liar[["clean", "y_fake"]].reset_index(drop=True).to_parquet(WORK / "clean_liar.parquet")
    report["liar2"] = {"file_sha256": sha256_of(SOURCES["liar"][1]), "rows": int(len(liar)),
                       "fake_share": round(float(liar["y_fake"].mean()), 4),
                       "median_tokens": float(liar["clean"].str.split().str.len().median())}
    (WORK / "prepare_report.json").write_text(json.dumps(report, indent=2))
    log("rows_clean", report["rows_clean"], "removed", removed, "reuters_rate", rate)


def load_split(name: str) -> pd.DataFrame:
    return pd.read_parquet(WORK / f"clean_{name}.parquet")


def stage_features() -> None:
    tr = load_split("train")
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_df=0.9, max_features=60000, sublinear_tf=True,
                          strip_accents="unicode", lowercase=True, dtype=np.float32)
    sp.save_npz(WORK / "X_train.npz", vec.fit_transform(tr["clean"]))  # vocabulary learned from train only
    for name in ("validation", "test", "liar"):
        sp.save_npz(WORK / f"X_{name}.npz", vec.transform(load_split(name)["clean"]))
    joblib.dump(vec, WORK / "vectorizer.joblib", compress=3)
    log("vocabulary size", len(vec.vocabulary_))


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    idx = np.digitize(p, np.linspace(0, 1, bins + 1)[1:-1])
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(total)


def metrics(y, pred, score) -> dict:
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "accuracy": round(float(accuracy_score(y, pred)), 4),
        "precision_fake": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall_fake": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1_fake": round(float(f1_score(y, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y, score)), 4),
        "pr_auc": round(float(average_precision_score(y, score)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "n": int(len(y)),
    }


def make_model(name: str):
    return {
        "logistic_regression": lambda: LogisticRegression(C=4.0, max_iter=2000, solver="liblinear", random_state=SEED),
        "naive_bayes": lambda: MultinomialNB(alpha=0.1),
        "linear_svm": lambda: LinearSVC(C=0.5, random_state=SEED),
        "random_forest": lambda: RandomForestClassifier(n_estimators=100, max_features="sqrt", min_samples_leaf=2,
                                                        n_jobs=2, random_state=SEED),
    }[name]()


def score_of(model, X) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return 1 / (1 + np.exp(-model.decision_function(X)))  # monotonic squashing, used only for ranking metrics


def stage_train(name: str) -> None:
    X = {s: sp.load_npz(WORK / f"X_{s}.npz") for s in ("train", "validation", "test", "liar")}
    y = {s: load_split(s)["y_fake"].to_numpy() for s in X}
    model = make_model(name)
    t = time.time()
    model.fit(X["train"], y["train"])
    train_s = time.time() - t
    t = time.time()
    scores = {s: score_of(model, X[s]) for s in ("validation", "test", "liar")}
    n_docs = X["validation"].shape[0] + X["test"].shape[0] + X["liar"].shape[0]
    infer_ms = (time.time() - t) / n_docs * 1000
    result = {
        "validation": metrics(y["validation"], (scores["validation"] >= 0.5).astype(int), scores["validation"]),
        "test": metrics(y["test"], (scores["test"] >= 0.5).astype(int), scores["test"]),
        "external_liar2": metrics(y["liar"], (scores["liar"] >= 0.5).astype(int), scores["liar"]),
        "train_seconds": round(train_s, 1), "inference_ms_per_doc": round(infer_ms, 3),
    }
    if name == "logistic_regression":
        result["calibration"] = {
            "ece_validation": round(ece(y["validation"], scores["validation"]), 4),
            "ece_test": round(ece(y["test"], scores["test"]), 4),
            "ece_external_liar2": round(ece(y["liar"], scores["liar"]), 4),
            "brier_test": round(float(brier_score_loss(y["test"], scores["test"])), 4),
            "brier_external_liar2": round(float(brier_score_loss(y["liar"], scores["liar"])), 4),
        }
        joblib.dump(model, WORK / "model_logistic_regression.joblib", compress=3)
    (WORK / f"result_{name}.json").write_text(json.dumps(result, indent=2))
    log(name, "test f1", result["test"]["f1_fake"], "liar f1", result["external_liar2"]["f1_fake"], f"({train_s:.0f}s)")


def stage_finalize() -> None:
    missing = [m for m in MODELS if not (WORK / f"result_{m}.json").exists()]
    if missing:
        raise SystemExit(f"train these models first: {missing}")
    report = json.loads((WORK / "prepare_report.json").read_text())
    comparison = {m: json.loads((WORK / f"result_{m}.json").read_text()) for m in MODELS}
    lr_res = comparison["logistic_regression"]
    calibration = lr_res.pop("calibration")
    vec = joblib.load(WORK / "vectorizer.joblib")
    lr = joblib.load(WORK / "model_logistic_regression.joblib")
    for d in (CKPT, REGISTRY, RESULTS, MANIFESTS):
        d.mkdir(parents=True, exist_ok=True)
    import platform
    import sklearn
    joblib.dump({"vectorizer": vec, "classifier": lr, "positive_label": "fake", "sklearn_version": sklearn.__version__},
                CKPT / "model.joblib", compress=3)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # The app reads this small file to check that the installed scikit-learn matches the one that trained the model.
    (CKPT / "model_meta.json").write_text(json.dumps(
        {"sklearn_version": sklearn.__version__, "python": platform.python_version(), "trained_at": now}, indent=2))
    liar_info = report.pop("liar2")
    manifest = {
        "name": "gonzaloa_fake_news", "version": "hf-main", "language": "en", "created_at": now,
        "source": "https://huggingface.co/datasets/GonzaloA/fake_news",
        "license": "License not stated on the dataset card; used for academic research only",
        "notes": "A mix of Kaggle fake-news collections; the card does not document sources or annotation. "
                 "Label 1 (real) was verified empirically against the wire-agency tag rate. Source artefacts such as "
                 "'(Reuters)' datelines are removed before training, but other source-style shortcuts may remain.",
        **report,
        "external_test_set": {"name": "liar2_test", "source": "https://huggingface.co/datasets/chengxuphd/liar2",
                              "license": "apache-2.0", **liar_info},
    }
    (MANIFESTS / "gonzaloa_fake_news.json").write_text(json.dumps(manifest, indent=2))
    result = {
        "model": MODEL_NAME, "version": MODEL_VERSION, "trained_at": now, "seed": SEED,
        "deployed_model": "logistic_regression",
        "features": {"type": "tfidf", "ngram_range": [1, 2], "max_features": 60000, "vocabulary_size": len(vec.vocabulary_)},
        "comparison": comparison, "calibration_logistic_regression": calibration,
        "interpretation": (
            "'test' measures separation of this collection's own held-out articles. 'external_liar2' is a different task "
            "(short political claims judged by fact-checkers) and shows how little the baseline transfers."),
    }
    (RESULTS / "text_baseline_en_metrics.json").write_text(json.dumps(result, indent=2))
    registry = {
        "module": "text", "name": MODEL_NAME, "version": MODEL_VERSION, "status": "trained_baseline",
        "artifact": "ai_models/checkpoints/text_baseline_en/model.joblib", "language": "en",
        "algorithm": "TF-IDF (1-2 grams) + Logistic Regression", "trained_at": now,
        "dataset": {"name": "gonzaloa_fake_news", "version": "hf-main", "rows_clean": report["rows_clean"],
                    "fake_share": report["label_distribution_fake_share"]},
        "metrics": {"test": lr_res["test"], "external_liar2": lr_res["external_liar2"], "calibration": calibration},
    }
    (REGISTRY / "text_baseline_en.json").write_text(json.dumps(registry, indent=2))
    log("finalized ->", CKPT / "model.joblib")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", default="all", choices=["all", "download", "prepare", "features", "train", "finalize"])
    ap.add_argument("--model", choices=MODELS, help="model for the 'train' stage (default: all four)")
    a = ap.parse_args()
    t0 = time.time()
    if a.stage in ("all", "download"):
        stage_download()
    if a.stage in ("all", "prepare"):
        stage_prepare()
    if a.stage in ("all", "features"):
        stage_features()
    if a.stage in ("all", "train"):
        for m in ([a.model] if a.model else MODELS):
            stage_train(m)
    if a.stage in ("all", "finalize"):
        stage_finalize()
    log(f"stage '{a.stage}' finished in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
