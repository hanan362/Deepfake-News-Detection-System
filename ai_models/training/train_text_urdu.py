"""Train and evaluate the Urdu text baseline for the Deepfake News Detection System.

Data: "Bend the Truth" (Amjad et al., 2020) as published on Hugging Face (community-datasets/urdu_fake_news):
638 training and 262 test news articles in five domains, labelled Fake or Real. It is the only openly downloadable Urdu
fake-news collection that was reachable when this was built, and it is small. Read the notes written to the manifest.

What this script does differently from the English one, and why
---------------------------------------------------------------
Almost every training article has a near-identical partner with the opposite label (the nearest neighbour of a training
article has the other label 88% of the time). A random cross-validation split puts one partner in the training fold and
the other in the validation fold, which makes a model look *worse* than chance (ROC AUC about 0.42). So articles are
grouped into connected components of cosine similarity >= 0.5 and cross-validation keeps each group in one fold.
The held-out test split has no such partners in the training data (median similarity 0.19 against 0.65 inside training).

Everything written to disk is a real measurement from this run. Run from the project root:
    python ai_models/training/train_text_urdu.py
"""
from __future__ import annotations

import json
import platform
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
from train_text_baseline import download_file, ece, log, metrics, sha256_of  # noqa: E402  (shared helpers)

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "datasets" / "raw" / "urdu_fake_news"
MANIFESTS = ROOT / "datasets" / "manifests"
CKPT = ROOT / "ai_models" / "checkpoints" / "text_baseline_ur"
REGISTRY = ROOT / "ai_models" / "model_registry"
RESULTS = ROOT / "ai_models" / "evaluation" / "results"
SEED = 42
MODEL_NAME, MODEL_VERSION = "text_baseline_ur", "1.0.0"
BASE = "https://huggingface.co/api/datasets/community-datasets/urdu_fake_news/parquet/default"
SOURCES = {"train": (f"{BASE}/train/0.parquet", RAW / "train.parquet"), "test": (f"{BASE}/test/0.parquet", RAW / "test.parquet")}
PAIR_SIMILARITY = 0.5
THRESHOLD = 0.80  # the same decision threshold as the English module (a configuration default, not tuned here)

_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_WS = re.compile(r"\s+")


def clean_urdu(text: str) -> str:
    """Same function as backend/app/ml/text_detection/preprocess.py::clean_urdu (a test keeps them identical)."""
    text = unicodedata.normalize("NFC", text or "")
    return _WS.sub(" ", _URL.sub(" ", text)).strip()


def load() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    for url, dest in SOURCES.values():
        download_file(url, dest)
    tr, te = pd.read_parquet(RAW / "train.parquet"), pd.read_parquet(RAW / "test.parquet")
    report = {"rows_raw": {"train": len(tr), "test": len(te)}}
    for d in (tr, te):
        d["x"] = d.news.map(clean_urdu)
        d["fake"] = (d.label == 0).astype(int)  # in this dataset label 0 is Fake and 1 is Real
    n_tr, n_te = len(tr), len(te)
    tr = tr.drop_duplicates("x").reset_index(drop=True)
    te = te[~te.x.isin(set(tr.x))].drop_duplicates("x").reset_index(drop=True)
    report["removed_duplicates"] = {"train": n_tr - len(tr), "test_duplicates_or_leaks_from_train": n_te - len(te)}
    report["rows_clean"] = {"train": len(tr), "test": len(te)}
    return tr, te, report


def pair_groups(texts: pd.Series) -> tuple[np.ndarray, dict]:
    """Group near-identical articles so that cross-validation never splits a pair (see the module docstring)."""
    vec = TfidfVectorizer(sublinear_tf=True).fit(texts)
    a = vec.transform(texts)
    sim = (a @ a.T).toarray()
    np.fill_diagonal(sim, 0)
    nearest = sim.argmax(1)
    _, groups = connected_components(sim >= PAIR_SIMILARITY, directed=False)
    return groups, {"nearest_neighbour_has_opposite_label": None, "n_groups": int(groups.max() + 1), "nearest": nearest}


def candidates() -> dict:
    def mk(kind, c):
        if kind == "word_1_2":
            vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=60000)
        else:
            vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=120000)
        return vec, LogisticRegression(C=c, max_iter=3000, solver="liblinear", random_state=SEED)
    return {f"{k}_C{c}": (k, c, mk) for k in ("word_1_2", "char_2_5") for c in (1, 4, 16, 64)}


def bootstrap_ci(y, p, fn, n=2000) -> list[float]:
    rng = np.random.default_rng(SEED)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if len(set(y[i])) < 2:
            continue
        vals.append(fn(y[i], p[i]))
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


def main() -> None:
    t0 = time.time()
    tr, te, report = load()
    ytr, yte = tr.fake.values, te.fake.values
    groups, ginfo = pair_groups(tr.x)
    opposite = float((ytr[ginfo["nearest"]] != ytr).mean())
    report["pairing"] = {"similarity_threshold": PAIR_SIMILARITY, "n_groups": ginfo["n_groups"],
                         "nearest_neighbour_has_opposite_label": round(opposite, 3)}
    log(f"train {len(tr)}, test {len(te)}, groups {ginfo['n_groups']}, opposite-label nearest neighbour {opposite:.1%}")

    # 1) Model selection by pair-aware cross-validation on the training split only.
    cv = StratifiedGroupKFold(5, shuffle=True, random_state=SEED)
    grid = {}
    for name, (kind, c, mk) in candidates().items():
        oof = np.zeros(len(tr))
        for a, b in cv.split(tr.x, ytr, groups):
            vec, clf = mk(kind, c)
            clf.fit(vec.fit_transform(tr.x.iloc[a]), ytr[a])
            oof[b] = clf.predict_proba(vec.transform(tr.x.iloc[b]))[:, 1]
        grid[name] = {"cv_roc_auc": round(float(roc_auc_score(ytr, oof)), 4), "cv_accuracy": round(float(accuracy_score(ytr, oof > 0.5)), 4)}
        log(f"{name:16s} grouped-CV AUC {grid[name]['cv_roc_auc']:.3f}  accuracy {grid[name]['cv_accuracy']:.3f}")
    best = max(grid, key=lambda k: grid[k]["cv_roc_auc"])
    kind, c, mk = candidates()[best]
    log(f"selected by grouped-CV AUC: {best}")

    # 2) The same selection with an ordinary random split, shown only to document why it is not used.
    from sklearn.model_selection import StratifiedKFold
    oof = np.zeros(len(tr))
    for a, b in StratifiedKFold(5, shuffle=True, random_state=SEED).split(tr.x, ytr):
        vec, clf = mk(kind, c)
        clf.fit(vec.fit_transform(tr.x.iloc[a]), ytr[a])
        oof[b] = clf.predict_proba(vec.transform(tr.x.iloc[b]))[:, 1]
    naive_cv_auc = round(float(roc_auc_score(ytr, oof)), 4)

    # 3) Final model on the whole training split, then one evaluation on the untouched test split.
    vec, clf = mk(kind, c)
    clf.fit(vec.fit_transform(tr.x), ytr)
    p = clf.predict_proba(vec.transform(te.x))[:, 1]
    test = metrics(yte, (p >= 0.5).astype(int), p)
    test["accuracy_ci95"] = bootstrap_ci(yte, p, lambda y, q: accuracy_score(y, q >= 0.5))
    test["roc_auc_ci95"] = bootstrap_ci(yte, p, roc_auc_score)
    conf = np.maximum(p, 1 - p)
    decided = conf >= THRESHOLD
    pred = (p >= 0.5).astype(int)
    coverage = {"threshold": THRESHOLD, "share_decided": round(float(decided.mean()), 4),
                "accuracy_when_decided": round(float((pred[decided] == yte[decided]).mean()), 4) if decided.any() else None,
                "n_decided": int(decided.sum())}
    calibration = {"ece_test": round(ece(yte, p), 4)}

    # 4) Trivial baselines the model has to beat.
    def length_features(d):
        return np.c_[np.log1p(d.x.str.split().str.len()), np.log1p(d.x.str.len())]
    length_model = LogisticRegression().fit(length_features(tr), ytr)
    pl = length_model.predict_proba(length_features(te))[:, 1]
    baselines = {
        "majority_accuracy": round(float(max(yte.mean(), 1 - yte.mean())), 4),
        "length_only": {"accuracy": round(float(accuracy_score(yte, pl >= 0.5)), 4), "roc_auc": round(float(roc_auc_score(yte, pl)), 4)},
    }
    by_category = {}
    names = {0: "business", 1: "health", 2: "sports", 3: "technology", 4: "showbiz"}  # class order on the dataset card
    for cat, g in te.groupby("category"):
        idx = g.index.values
        by_category[names.get(int(cat), str(cat))] = {"n": int(len(idx)), "accuracy": round(float((pred[idx] == yte[idx]).mean()), 4)}

    # 5) Write everything.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for d in (CKPT, REGISTRY, RESULTS, MANIFESTS):
        d.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vec, "classifier": clf, "positive_label": "fake", "sklearn_version": sklearn.__version__},
                CKPT / "model.joblib", compress=3)
    (CKPT / "model_meta.json").write_text(json.dumps(
        {"sklearn_version": sklearn.__version__, "python": platform.python_version(), "trained_at": now}, indent=2))
    manifest = {
        "name": "urdu_fake_news", "version": "hf-parquet", "language": "ur", "created_at": now,
        "source": "https://huggingface.co/datasets/community-datasets/urdu_fake_news",
        "paper": "Amjad et al., Bend the Truth: A Benchmark Dataset for Fake News Detection in Urdu and Its Evaluation (J. Intelligent & Fuzzy Systems, 2020)",
        "license": "unknown on the dataset card; used for academic research only",
        "files": {k: {"sha256": sha256_of(dest), "bytes": dest.stat().st_size} for k, (_, dest) in SOURCES.items()},
        **report,
        "notes": ("Five news domains. In the training split almost every Fake article has a near-identical Real partner "
                  "(the nearest neighbour has the opposite label for the share given in 'pairing'), so pair-aware "
                  "cross-validation was used. The test split has no such partners in the training data. There is no "
                  "second Urdu collection to test against, so nothing here shows that the model works on Urdu news "
                  "from other sources. Roman Urdu is not covered."),
    }
    (MANIFESTS / "urdu_fake_news.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    result = {
        "model": MODEL_NAME, "version": MODEL_VERSION, "trained_at": now, "seed": SEED, "selected": best,
        "features": {"type": "tfidf", "analyzer": "char_wb" if kind == "char_2_5" else "word",
                     "ngram_range": [2, 5] if kind == "char_2_5" else [1, 2], "vocabulary_size": len(vec.vocabulary_), "C": c},
        "selection": {"method": "5-fold StratifiedGroupKFold on the training split, groups = near-duplicate articles",
                      "grid": grid, "naive_random_cv_roc_auc_of_selected": naive_cv_auc,
                      "why_not_random_cv": "pairs are split across folds, which makes the result worse than chance"},
        "test": test, "decision_coverage": coverage, "calibration": calibration, "baselines": baselines,
        "by_category_accuracy": by_category,
        "interpretation": ("Measured on 'Bend the Truth' only. The test split is small, so the confidence intervals are "
                           "wide. There is no external Urdu test set, so how this behaves on other Urdu news is unknown."),
    }
    (RESULTS / "text_baseline_ur_metrics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    registry = {
        "module": "text_ur", "name": MODEL_NAME, "version": MODEL_VERSION, "status": "experimental",
        "artifact": "ai_models/checkpoints/text_baseline_ur/model.joblib", "language": "ur",
        "algorithm": ("TF-IDF (character 2-5 grams) + Logistic Regression" if kind == "char_2_5"
                      else "TF-IDF (words 1-2 grams) + Logistic Regression"), "trained_at": now,
        "dataset": {"name": "urdu_fake_news", "version": "hf-parquet", "rows_clean": report["rows_clean"],
                    "fake_share": round(float(ytr.mean()), 4)},
        "metrics": {"test": test, "group_cv_roc_auc": grid[best]["cv_roc_auc"], "calibration": calibration,
                    "baselines": baselines},
    }
    (REGISTRY / "text_baseline_ur.json").write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    log(f"test accuracy {test['accuracy']} {test['accuracy_ci95']}  AUC {test['roc_auc']} {test['roc_auc_ci95']}  "
        f"majority {baselines['majority_accuracy']}  length-only AUC {baselines['length_only']['roc_auc']}")
    log(f"at threshold {THRESHOLD}: decided {coverage['share_decided']:.0%}, accuracy there {coverage['accuracy_when_decided']}")
    log(f"finished in {time.time() - t0:.0f}s -> {CKPT / 'model.joblib'}")


if __name__ == "__main__":
    main()
