"""Measures the headline-against-text check (app.ml.corroboration.consistency) on real articles and on texts that were changed.

Every pair goes, unchanged, through the production function with the real inference model, so the figures describe exactly what
the application does. No internet is needed; nothing is trained.

Sets (ai_models/evaluation/headline_body/, collected with training/collect_headline_body_data.py):
  articles.json   the development set: real articles (headline from an outlet's feed, first 250 words from its page). The
                  thresholds in consistency.py were looked at on THIS set, so it is not an independent test of them.
  test.json       a second set collected afterwards, with other articles. The rules were frozen before it was read. This is the
                  honest measurement.

Kinds of pair built from an article (headline h, text b):
  matched          h with its own text b                               expected: not flagged (ideally "consistent")
  other_story      h with the text of an article about another story   expected: flagged
  numbers_changed  h with b where every number is replaced             expected: flagged   (only when h has a number that b has)
  names_changed    h with b where the names of h are replaced          expected: flagged   (only when h has a name that b has)
  contradicting    h with a text written by hand that says the opposite   expected: flagged
  fabricated       h with a text written by hand that agrees with h and adds invented details   expected: NOT flagged (the known limit)
"contradicting" and "fabricated" texts are in handwritten_<set>.json; they were written by the same person who wrote the rules, so
they are not an independent sample of what a person who wants to deceive would write.
"Flagged" means status contradicts, unrelated or details_differ (the statuses that stop a "Likely Real").

Writes ai_models/evaluation/results/headline_body.json.
Usage: python ai_models/training/evaluate_headline_body.py [dev,test,test2|both]"""
from __future__ import annotations

import json
import math
import os
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.corroboration import consistency  # noqa: E402
from app.ml.corroboration.check import overlap  # noqa: E402
from app.ml.fact_checking.nli import get_nli  # noqa: E402

DATA = ROOT / "ai_models" / "evaluation" / "headline_body"
RESULTS = Path(os.environ.get("HEADLINE_BODY_RESULTS") or ROOT / "ai_models" / "evaluation" / "results" / "headline_body.json")
SETS = {"dev": "articles.json", "test": "test.json", "test2": "test2.json", "test3": "test3.json",
        "test2_full": "test2.json"}          # the same articles as test2, but compared with their whole text (see FULL_TEXT)
FULL_TEXT = {"test3", "test2_full"}          # sets whose texts are the whole article, as the application reads it; the others are the first 250 words
_FUNCTION_START = {"the", "a", "an", "after", "as", "in", "on", "at", "for", "with", "how", "why", "what", "when", "will", "can"}


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0.0, (c - h) / d), 3), round(min(1.0, (c + h) / d), 3)]


def change_numbers(body: str) -> str:
    """Every number of the text (digits, or a number word) becomes a different number (n -> 7n + 13), so none of the headline's numbers is left."""
    body = consistency._normalise(body)  # number words and "1,200" become plain digits
    return re.sub(r"(?<![\w.])(\d+)(?!\w)", lambda m: str(int(m.group(1)) * 7 + 13), body)


def headline_numbers_in_body(headline: str, body: str) -> bool:
    """True when a number of the headline (digits or a number word, "five" = 5) also appears in the text, so that changing the
    numbers of the text really makes it disagree with the headline."""
    norm = consistency._normalise
    nums = set(re.findall(r"\d+", norm(headline)))
    return bool(nums & set(re.findall(r"\d+", norm(body))))


def headline_names(headline: str) -> list[str]:
    toks = re.findall(r"[A-Za-z][A-Za-z'’\-]+", headline)
    words = [t for t in toks if len(t) > 3]
    if len(words) >= 4 and sum(t[0].isupper() for t in words) / len(words) >= 0.6:  # Title Case headline: capitals say nothing
        return []
    first = toks[0].lower() if toks else ""
    return [t for i, t in enumerate(toks) if t[0].isupper() and len(t) > 2 and not (i == 0 and first in _FUNCTION_START)]


def change_names(headline: str, body: str, pool: list[str]) -> str | None:
    names = [n for n in dict.fromkeys(headline_names(headline)) if re.search(rf"\b{re.escape(n)}\w*", body)]
    if not names:
        return None
    out = body
    for n, repl in zip(names, pool):
        out = re.sub(rf"\b{re.escape(n)}\w*", repl, out)  # also "Korean" for "Korea"
    return out


def load(name: str) -> list[dict]:
    return json.loads((DATA / SETS[name]).read_text(encoding="utf-8"))


def pairs_for(articles: list[dict], name: str, seed: int = 11) -> list[dict]:
    rng = random.Random(seed)
    if name in FULL_TEXT:   # the whole text takes the place of the first 250 words everywhere below
        articles = [{**a, "body": a["full"]} for a in articles if a.get("full")]
    hand_path = DATA / f"handwritten_{name}.json"
    hand = json.loads(hand_path.read_text(encoding="utf-8")) if hand_path.exists() else {}
    name_pool = sorted({n for a in articles for n in headline_names(a["headline"]) if len(n) > 4})
    out = []
    for a in articles:
        out.append({"id": a["id"], "kind": "matched", "headline": a["headline"], "text": a["body"], "outlet": a["outlet"]})
        others = [b for b in articles if b["id"] != a["id"] and overlap(a["headline"], b["headline"]) < 0.2 and overlap(b["headline"], a["headline"]) < 0.2]
        if others:
            b = rng.choice(others)
            out.append({"id": a["id"], "kind": "other_story", "headline": a["headline"], "text": b["body"], "outlet": a["outlet"], "from": b["id"]})
        if headline_numbers_in_body(a["headline"], a["body"]):
            out.append({"id": a["id"], "kind": "numbers_changed", "headline": a["headline"], "text": change_numbers(a["body"]), "outlet": a["outlet"]})
        repl = rng.sample([n for n in name_pool if not re.search(rf"\b{re.escape(n)}\b", a["body"])], 6)
        changed = change_names(a["headline"], a["body"], repl)
        if changed:
            out.append({"id": a["id"], "kind": "names_changed", "headline": a["headline"], "text": changed, "outlet": a["outlet"]})
        for kind in ("contradicting", "fabricated"):
            if a["id"] in hand and hand[a["id"]].get(kind):
                out.append({"id": a["id"], "kind": kind, "headline": a["headline"], "text": hand[a["id"]][kind], "outlet": a["outlet"]})
    return out


FLAGGED = consistency.MISMATCH
EXPECT_FLAGGED = {"other_story", "numbers_changed", "names_changed", "contradicting"}


def run(name: str) -> dict:
    nli = get_nli()
    articles = load(name)
    pairs = pairs_for(articles, name)
    rows = []
    for p in pairs:
        r = consistency.check(p["headline"], p["text"], nli)
        rows.append({"id": p["id"], "kind": p["kind"], "outlet": p["outlet"], "status": r["status"], "reason": r.get("reason"),
                     "missing": r.get("missing"), "best": r.get("best"), "headline": p["headline"], "text_start": p["text"][:160]})
    summary = {}
    for kind in ["matched", "other_story", "numbers_changed", "names_changed", "contradicting", "fabricated"]:
        sel = [r for r in rows if r["kind"] == kind]
        if not sel:
            continue
        counts = Counter(r["status"] for r in sel)
        flagged = sum(counts[s] for s in FLAGGED)
        entry = {"n": len(sel), "statuses": dict(counts), "flagged": flagged, "flagged_ci": wilson(flagged, len(sel))}
        if kind == "matched":
            entry["consistent"] = counts["consistent"]
            entry["consistent_ci"] = wilson(counts["consistent"], len(sel))
        summary[kind] = entry
    return {"set": name, "articles": len(articles), "summary": summary, "rows": rows}


if __name__ == "__main__":
    # python evaluate_headline_body.py dev,test,test2     (or one name; "both" = all three). The results of each set are written
    # into headline_body.json next to the others, with the checksum of the rules that produced them.
    import hashlib

    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    names = list(SETS) if which == "both" else which.split(",")
    out = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else {"results": {}}
    out["thresholds"] = {k: getattr(consistency, k) for k in (
        "LEAD_SENTENCES", "SUPPORT_ENTAILMENT", "CONTRADICT_PROBABILITY", "CONTRADICT_OVERLAP", "UNRELATED_OVERLAP", "SAME_SUBJECT_OVERLAP")}
    out["rules_sha256"] = hashlib.sha256(Path(consistency.__file__).read_bytes()).hexdigest()
    out["run_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for n in names:
        res = run(n)
        res["run_at"], res["rules_sha256"] = out["run_at"], out["rules_sha256"]
        out["results"][n] = res
        print(n, json.dumps(res["summary"], indent=1), flush=True)
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        RESULTS.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("written", RESULTS)
