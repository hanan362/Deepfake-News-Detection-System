"""Measures the headline-corroboration check by replaying SAVED news-search results through the production code.

For every test headline the saved search results are fed, unchanged, to app.ml.corroboration.check.corroborate with the real
inference model, so the figures describe exactly what the application does. No internet is needed; nothing is trained.

Test sets (ai_models/evaluation/corroboration/):
  sets/results        76 headlines collected 22-23 Nov 2026: 42 real headlines read from outlet feeds the same day, 14 "distorted"
                      copies of them (one number, place or verb changed) and 20 invented headlines. The two thresholds in
                      check.py were chosen from a small grid on THIS set, so it is not an independent test of them.
  sets_old/results    60 older headlines (30 real, 30 fake) from the project's text dataset: this measures how the check behaves
                      on news a news search no longer returns.
  heldout_sets/...    a fresh set collected after the rules were fixed (see training/collect_corroboration_data.py): the honest test.

For real headlines two figures are given: with the outlet the headline was read from counted (what happens when an article
is pasted as text) and with it excluded (what happens when the address is analysed, since a site cannot confirm itself).

Writes ai_models/evaluation/results/corroboration.json.   Usage: python ai_models/training/evaluate_corroboration.py"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.corroboration import check  # noqa: E402
from app.ml.corroboration.news_search import NewsHit  # noqa: E402
from app.ml.fact_checking.nli import get_nli  # noqa: E402
from app.ml.url_analysis.source import directory, match_entry  # noqa: E402

DATA = ROOT / "ai_models" / "evaluation" / "corroboration"
OUT = ROOT / "ai_models" / "evaluation" / "results" / "corroboration.json"
SETS = [
    ("current", "sets.json", "results.json", "Headlines read from outlet feeds on 22-23 Nov 2026, distorted copies of them, and invented headlines. The thresholds were chosen from a small grid on this set."),
    ("older_news", "sets_old.json", "results_old.json", "Older real and fake headlines from the project's text dataset. A news search rarely returns old news."),
    ("heldout", "heldout_sets.json", "heldout_results.json", "A fresh set collected after the rules were fixed. Not used to choose any threshold."),
    ("fresh2", "fresh2_sets.json", "fresh2_results.json", "A third set (23 Nov 2026), larger: 12 headlines from each of seven outlets, and automatic one-word or one-number distortions of them. "
     "Collected after the rules and the 429 handling were final. Not used to choose or change anything."),
]


class Replay:
    name = "saved results"

    def __init__(self, rows):
        self.rows = rows

    def search(self, query, limit=12):
        return [NewsHit(title=r["title"], outlet=r.get("outlet"), site_url=r.get("site_url") or r.get("domain"), link=r.get("link"),
                        published=r.get("published") or r.get("pubDate")) for r in self.rows][:limit]


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round(max(0.0, (c - h) / d), 3), round(min(1.0, (c + h) / d), 3)]


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    out = {"n": n}
    for s in ("corroborated", "disputed", "not_found", "unavailable"):
        out[s] = sum(r["status"] == s for r in rows)
    out["corroborated_rate"] = round(out["corroborated"] / n, 3) if n else None
    out["corroborated_95ci"] = wilson(out["corroborated"], n)
    out["disputed_rate"] = round(out["disputed"] / n, 3) if n else None
    out["with_any_search_result"] = sum(r["results_read"] > 0 for r in rows)
    out["not_found_with_related_coverage"] = sum(r["status"] == "not_found" and bool(r.get("related")) for r in rows)  # shown to the reader; no effect on the verdict
    return out


def main() -> None:
    nli = get_nli()
    if not nli.available:
        raise SystemExit(nli.problem())
    report = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "nli_model": nli.model_id, "nli_revision": getattr(nli, "revision", None),
              "directory_version": directory()["version"], "directory_entries": len(directory()["entries"]), "rules": check.RULES,
              "thresholds": {"support_overlap": check.SUPPORT_OVERLAP, "support_entailment": check.SUPPORT_ENTAILMENT,
                             "contradict_overlap": check.CONTRADICT_OVERLAP, "contradict_probability": check.CONTRADICT_PROBABILITY},
              "limits": check.LIMITS, "sets": {}}
    for name, sets_file, results_file, description in SETS:
        sp, rp = DATA / sets_file, DATA / results_file
        if not (sp.exists() and rp.exists()):
            print(f"{name}: files not found, skipped")
            continue
        saved = {x["id"]: x for x in json.loads(rp.read_text(encoding="utf-8"))}
        items = json.loads(sp.read_text(encoding="utf-8"))
        rows, failed = [], 0
        for x in items:
            got = saved.get(x["id"], {})
            if got.get("results") is None:
                failed += 1  # the search itself failed when the data was collected: not counted either way
                continue
            own = match_entry(x["own_outlet"]) if x.get("own_outlet") else None
            for variant, exclude in (("own_counted", None), ("own_excluded", own["name"] if own else None)):
                if variant == "own_excluded" and not own:
                    continue
                r = check.corroborate(x["headline"], Replay(got["results"]), nli, exclude_outlet=exclude)
                rows.append({"id": x["id"], "kind": x["kind"], "variant": variant, "headline": x["headline"], "status": r["status"],
                             "results_read": r["results_read"], "listed_outlet_results": r["listed_outlet_results"],
                             "outlets": [o["name"] for o in r["outlets"]], "related": [o["name"] for o in r.get("related", [])]})
        kinds: dict[str, dict] = {}
        for kind in sorted({r["kind"] for r in rows}):
            for variant in ("own_counted", "own_excluded"):
                sel = [r for r in rows if r["kind"] == kind and (r["variant"] == variant or (variant == "own_counted" and r["variant"] == "own_counted"))]
                if variant == "own_excluded":
                    sel = [r for r in rows if r["kind"] == kind and r["variant"] == "own_excluded"]
                if sel:
                    kinds[kind if variant == "own_counted" else kind + " (own outlet excluded)"] = summarise(sel)
        report["sets"][name] = {"description": description, "headlines": len(items), "search_failed_at_collection": failed, "kinds": kinds,
                                "items": rows}
        print(f"\n{name}: {len(items)} headlines ({failed} without search data)")
        for k, v in kinds.items():
            print(f"  {k:36s} n={v['n']:3d}  corroborated {v['corroborated']:3d} ({v['corroborated_rate']:.0%}, 95% CI {v['corroborated_95ci']})  disputed {v['disputed']:3d}  not found {v['not_found']:3d} (related coverage shown for {v['not_found_with_related_coverage']})")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("\nwrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
