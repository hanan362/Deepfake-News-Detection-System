"""Measures the whole evidence check (retrieval + stance + verdict) on claims whose truth is known.

Why this exists: the FEVER evaluation (evaluate_evidence_nli.py) hands the model the gold evidence sentence, so it measures the
stance model alone. It cannot show what a user sees, because in use the evidence is found by a Wikipedia search and a wrong
sentence can be picked. This script runs the real pipeline on short factual claims, 20 true and 20 false in each of two sets:

  SET_A  written first and used while the pipeline was being changed (so its numbers are optimistic)
  SET_B  written afterwards and not looked at until the changes were final (the honest figure)

Both sets are small, written by the developers, and about well-known facts that Wikipedia covers. They show how the check behaves,
not how accurate it is on real news. A claim counts as correct when a true claim is Supported or a false one Contradicted, wrong
when it is the other way round, and Mixed Evidence / Insufficient Evidence are reported separately (no call is made).

Search results are read from ai_models/evaluation/cache/evidence_live_retrieval.json so that the run is repeatable and needs no
network; --refresh fetches them again from Wikipedia. --baseline re-creates the pipeline as it was before the changes made on
2026-11-22 (no pronunciation or pronoun handling, three sentences per page, the DistilBERT model) for comparison.

The retrieval has two searches since 2026-11-23: the claim's own words (cache above) and the claim's subject alone (second cache).
--no-subject replays only the first, i.e. the pipeline as it was on 2026-11-22 after the first round of changes.

Run from the project root:  python ai_models/training/evaluate_evidence_live.py [--refresh] [--baseline] [--no-subject]"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.fact_checking import verify  # noqa: E402
from app.ml.fact_checking.nli import DEFAULT_MODEL, NliModel  # noqa: E402
from app.ml.fact_checking.providers import Evidence, ProviderResult, WikipediaProvider, merge_evidence, subject_phrase  # noqa: E402

CACHE = ROOT / "ai_models" / "evaluation" / "cache" / "evidence_live_retrieval.json"
SUBJECT_CACHE = ROOT / "ai_models" / "evaluation" / "cache" / "evidence_live_subject_raw.json"  # raw answers of the subject-only search
OUT = ROOT / "ai_models" / "evaluation" / "results" / "evidence_live_claims.json"
LEGACY_MODEL = "typeform/distilbert-base-uncased-mnli"

SET_A_TRUE = [
    "The Eiffel Tower is located in Paris, France.",
    "Apollo 11 landed on the Moon in 1969.",
    "Pakistan won the 1992 Cricket World Cup.",
    "Mount Everest is the highest mountain above sea level.",
    "The Great Wall of China is located in China.",
    "Albert Einstein developed the theory of relativity.",
    "The Nile flows through Egypt.",
    "Lahore is a city in Pakistan.",
    "Leonardo da Vinci painted the Mona Lisa.",
    "The Amazon River is in South America.",
    "Water boils at 100 degrees Celsius at sea level.",
    "Tokyo is the capital of Japan.",
    "Marie Curie won the Nobel Prize in Physics.",
    "The Taj Mahal is located in Agra, India.",
    "William Shakespeare wrote Hamlet.",
    "The Titanic sank in 1912.",
    "Muhammad Ali Jinnah was the founder of Pakistan.",
    "The Pacific Ocean is the largest ocean on Earth.",
    "Isaac Newton formulated the laws of motion.",
    "The Berlin Wall fell in 1989.",
]
SET_A_FALSE = [
    "The Eiffel Tower is located in Rome, Italy.",
    "Apollo 11 landed on the Moon in 1975.",
    "India won the 1992 Cricket World Cup.",
    "Mount Everest is located in South America.",
    "The Great Wall of China is located in Brazil.",
    "Albert Einstein developed the theory of evolution.",
    "The Nile flows through Canada.",
    "Lahore is a city in Japan.",
    "Pablo Picasso painted the Mona Lisa.",
    "The Amazon River is in Africa.",
    "Water boils at 50 degrees Celsius at sea level.",
    "Sydney is the capital of Australia.",
    "Marie Curie won the Nobel Prize in Literature.",
    "The Taj Mahal is located in Delhi, India.",
    "Charles Dickens wrote Hamlet.",
    "The Titanic sank in 1920.",
    "Mahatma Gandhi was the founder of Pakistan.",
    "The Atlantic Ocean is the largest ocean on Earth.",
    "Charles Darwin formulated the laws of motion.",
    "The Berlin Wall fell in 1999.",
]
SET_B_TRUE = [
    "The Statue of Liberty is located in New York City.",
    "Neil Armstrong was the first person to walk on the Moon.",
    "The Sahara is a desert in Africa.",
    "Barack Obama served as the 44th president of the United States.",
    "The Great Barrier Reef is located off the coast of Queensland, Australia.",
    "Mount Fuji is the highest mountain in Japan.",
    "Thomas Edison invented the phonograph.",
    "The Colosseum is located in Rome, Italy.",
    "Karachi is the largest city in Pakistan.",
    "Mahatma Gandhi was born in Porbandar, India.",
    "The Pyramids of Giza are located in Egypt.",
    "Charles Darwin wrote On the Origin of Species.",
    "The Amazon rainforest is located mainly in Brazil.",
    "Beethoven composed the Ninth Symphony.",
    "The Danube flows through Vienna.",
    "Venus is the second planet from the Sun.",
    "Nelson Mandela became president of South Africa in 1994.",
    "The Burj Khalifa is located in Dubai.",
    "Mozart was born in Salzburg.",
    "The Wright brothers made the first powered airplane flight in 1903.",
]
SET_B_FALSE = [
    "The Statue of Liberty is located in Los Angeles.",
    "Yuri Gagarin was the first person to walk on the Moon.",
    "The Sahara is a desert in Asia.",
    "Barack Obama served as the 40th president of the United States.",
    "The Great Barrier Reef is located off the coast of Spain.",
    "Mount Fuji is the highest mountain in China.",
    "Thomas Edison invented the printing press.",
    "The Colosseum is located in Athens, Greece.",
    "Islamabad is the largest city in Pakistan.",
    "Mahatma Gandhi was born in London, England.",
    "The Pyramids of Giza are located in Mexico.",
    "Charles Darwin wrote Pride and Prejudice.",
    "The Amazon rainforest is located mainly in Germany.",
    "Beethoven composed The Four Seasons.",
    "The Danube flows through Tokyo.",
    "Mars is the second planet from the Sun.",
    "Nelson Mandela became president of South Africa in 1964.",
    "The Burj Khalifa is located in Paris.",
    "Mozart was born in Berlin.",
    "The Wright brothers made the first powered airplane flight in 1953.",
]


class Cached:
    name = "wikipedia"

    def __init__(self, raw: dict, subject_raw: dict | None = None):
        subject_pages = WikipediaProvider._pages(subject_raw["data"]) if subject_raw and subject_raw["status"] == "ok" else []
        items = merge_evidence(subject_pages, [Evidence(**e) for e in raw["evidence"]])
        self.result = ProviderResult("wikipedia", "ok" if items else raw["status"], raw["message"], items)

    def search(self, claim: str) -> ProviderResult:
        return self.result


def refresh(claims: list[str]) -> dict:
    import dataclasses
    wp, out = WikipediaProvider(), {}
    for claim in claims:
        for _ in range(4):
            r = wp.search(claim)
            if r.status in ("ok", "no_results"):
                break
            time.sleep(3)
        out[claim] = {"status": r.status, "message": r.message, "evidence": [dataclasses.asdict(e) for e in r.evidence]}
        print(f"fetched {len(out)}/{len(claims)}", flush=True)
    CACHE.write_text(json.dumps({"about": "Wikipedia search results (CC BY-SA 4.0), refreshed by evaluate_evidence_live.py",
                                 "fetched_at": datetime.now(timezone.utc).date().isoformat(), "retrieval": out}, ensure_ascii=False), encoding="utf-8")
    return out


def score(claims_true: list[str], claims_false: list[str], verdicts: dict[str, str]) -> dict:
    def count(claims: list[str], good: str, bad: str) -> dict:
        v = [verdicts[c] for c in claims]
        return {"correct": v.count(good), "wrong": v.count(bad), "mixed": v.count("Mixed Evidence"), "no_call": v.count("Insufficient Evidence")}
    t, f = count(claims_true, "Supported", "Contradicted"), count(claims_false, "Contradicted", "Supported")
    return {"true_claims": t, "false_claims": f, "correct": t["correct"] + f["correct"], "wrong": t["wrong"] + f["wrong"], "n": len(claims_true) + len(claims_false)}


def main(argv: list[str]) -> None:
    sets = {"SET_A (used while tuning)": (SET_A_TRUE, SET_A_FALSE), "SET_B (held out)": (SET_B_TRUE, SET_B_FALSE)}
    everything = [c for t, f in sets.values() for c in t + f]
    cache = refresh(everything) if "--refresh" in argv else json.loads(CACHE.read_text(encoding="utf-8"))["retrieval"]
    baseline = "--baseline" in argv
    subject_cache = {} if "--no-subject" in argv or baseline else json.loads(SUBJECT_CACHE.read_text(encoding="utf-8"))["results"]
    if baseline:
        verify.strip_pronunciation, verify.namesake_titles = (lambda t: t), (lambda titles, claim: set())
        verify.name_the_subject, verify.SENTENCES_PER_PASSAGE = (lambda s, t: s), 3
    nli = NliModel(LEGACY_MODEL if baseline else DEFAULT_MODEL)
    if not nli.available:
        raise SystemExit(nli.problem())
    results, per_claim = {}, {}
    for name, (t, f) in sets.items():
        verdicts = {c: verify.verify_claim(c, [Cached(cache[c], subject_cache.get(subject_phrase(c) or ""))], nli)["verdict"] for c in t + f}
        results[name] = score(t, f, verdicts)
        per_claim[name] = verdicts
        print(name, json.dumps(results[name]))
    pipeline = "baseline (before 2026-11-22)" if baseline else ("claim-words search only (2026-11-22)" if "--no-subject" in argv else "current (claim-words search + subject search)")
    out = {"evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pipeline": pipeline,
           "nli_model": nli.model_id, "stance_threshold": verify.STANCE_THRESHOLD, "retrieval": "cached Wikipedia search results (see script)", "sets": results, "verdicts": per_claim,
           "caution": "Small, developer-written sets about well-known facts. SET_A was used while tuning, SET_B was not. Not a measure of accuracy on news."}
    path = OUT.with_name("evidence_live_claims_baseline.json") if baseline else (OUT.with_name("evidence_live_claims_no_subject.json") if "--no-subject" in argv else OUT)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print("wrote", path.relative_to(ROOT))


if __name__ == "__main__":
    main(sys.argv[1:])
