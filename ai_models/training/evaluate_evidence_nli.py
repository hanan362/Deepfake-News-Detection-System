"""Measures the stance model used by the evidence module on FEVER claims with their GOLD evidence sentences.

What this does and does not show: each claim is given the evidence sentence(s) FEVER annotators selected, so this
measures the inference model alone. It does not measure retrieval (finding evidence), which is where a real system
loses most claims. Nothing is trained: the model is pretrained (MNLI), and this script only evaluates it.

Writes ai_models/evaluation/results/evidence_nli_fever.json, datasets/manifests/fever_gold_evidence.json and
ai_models/model_registry/evidence_nli.json.   Usage: python ai_models/training/evaluate_evidence_nli.py [per_class]"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.fact_checking.nli import DEFAULT_MODEL, NliModel  # noqa: E402
from app.ml.fact_checking.verify import STANCE_THRESHOLD  # noqa: E402

URL = "https://huggingface.co/api/datasets/copenlu/fever_gold_evidence/parquet/default/validation/0.parquet"
RAW = ROOT / "datasets" / "raw" / "fever_gold" / "validation.parquet"
SEED = 42


def clean(t: str) -> str:
    for a, b in (("-LRB-", "("), ("-RRB-", ")"), ("-LSB-", "["), ("-RSB-", "]"), ("-COLON-", ":")):
        t = t.replace(a, b)
    return " ".join(t.split())


def premise(evidence) -> str:
    sentences = [clean(str(e[2])) for e in evidence if len(e) >= 3 and str(e[2]).strip()]
    return " ".join(sentences[:2])


def main(per_class: int = 600) -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if not RAW.exists():
        req = urllib.request.Request(URL, headers={"User-Agent": "ddn-eval"})
        RAW.write_bytes(urllib.request.urlopen(req, timeout=60).read())  # noqa: S310
    df = pd.read_parquet(RAW)
    df = df[df.label.isin(["SUPPORTS", "REFUTES"])].copy()
    df["premise"] = df.evidence.map(premise)
    df = df[df.premise.str.len() > 20]
    sample = pd.concat([g.sample(min(per_class, len(g)), random_state=SEED) for _l, g in df.groupby("label")]).reset_index(drop=True)
    nli = NliModel(DEFAULT_MODEL)
    if not nli.available:
        raise SystemExit(nli.problem())
    t0 = time.time()
    probs = nli.predict(list(zip(sample.premise, sample.claim)))
    elapsed = time.time() - t0
    pe = np.array([p["entailment"] for p in probs])
    pc = np.array([p["contradiction"] for p in probs])
    y = (sample.label == "SUPPORTS").to_numpy()
    forced = pe >= pc  # entailment vs contradiction, no abstaining
    decided = (pe >= STANCE_THRESHOLD) | (pc >= STANCE_THRESHOLD)
    pred = pe >= STANCE_THRESHOLD
    rng = np.random.default_rng(SEED)
    idx = np.flatnonzero(decided)
    boot = [float((pred[s] == y[s]).mean()) for s in (rng.choice(idx, len(idx)) for _ in range(1000))]
    tp, fn = int(((pred == y) & decided & y).sum()), int((decided & y & ~pred).sum())
    tn, fp = int(((pred == y) & decided & ~y).sum()), int((decided & ~y & pred).sum())
    res = {
        "model": DEFAULT_MODEL, "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": SEED,
        "what_was_measured": "Stance of a claim given FEVER's gold evidence sentences (SUPPORTS vs REFUTES). Retrieval is NOT measured.",
        "n": int(len(sample)), "per_class": {"SUPPORTS": int(y.sum()), "REFUTES": int((~y).sum())},
        "stance_threshold": STANCE_THRESHOLD,
        "forced_choice_accuracy": round(float((forced == y).mean()), 4),
        "at_threshold": {
            "share_decided": round(float(decided.mean()), 4), "n_decided": int(decided.sum()),
            "accuracy_when_decided": round(float((pred[decided] == y[decided]).mean()), 4),
            "accuracy_ci95": [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)],
            "confusion_when_decided": {"supports_correct": tp, "supports_missed_as_refutes": fn, "refutes_correct": tn, "refutes_called_supports": fp},
        },
        "baselines": {"majority_accuracy": round(float(max(y.mean(), 1 - y.mean())), 4)},
        "seconds_per_pair": round(elapsed / len(sample), 4),
        "interpretation": ("With the evidence handed over, the model separates supporting from contradicting sentences well above chance, "
                           "and at the 85% threshold it abstains on the rest. A real check must first FIND the evidence, which this does "
                           "not test; expect far lower coverage in use. The model never sees whether the evidence is itself true."),
    }
    out = ROOT / "ai_models" / "evaluation" / "results" / "evidence_nli_fever.json"
    out.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    manifest = {"name": "fever_gold_evidence", "version": "validation", "source": "https://huggingface.co/datasets/copenlu/fever_gold_evidence",
                "paper": "Thorne et al., FEVER: a large-scale dataset for Fact Extraction and VERification (NAACL 2018)",
                "license": "CC BY-SA 3.0 (FEVER, built on Wikipedia)", "file_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
                "rows_validation": int(len(pd.read_parquet(RAW))), "rows_used": int(len(sample)), "sampling": f"{per_class} per class, seed {SEED}, SUPPORTS and REFUTES only"}
    (ROOT / "datasets" / "manifests" / "fever_gold_evidence.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    reg = {"module": "evidence", "name": "evidence_nli", "version": "1.0.0", "status": "pretrained", "language": "en",
           "algorithm": f"Pretrained MNLI model ({DEFAULT_MODEL}); not trained here",
           "dataset": {"name": "fever_gold_evidence", "version": "validation", "rows_clean": {"evaluated": int(len(sample))}},
           "metrics": {"fever_gold": {k: res[k] for k in ("n", "forced_choice_accuracy", "at_threshold", "baselines")}}}
    (ROOT / "ai_models" / "model_registry" / "evidence_nli.json").write_text(json.dumps(reg, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("n", "forced_choice_accuracy", "at_threshold", "baselines", "seconds_per_pair")}, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 600)
