"""Collects a FRESH test set for the headline-corroboration check, using the production search code.

What it does: (1) reads current headlines from the public RSS feeds of eight well-known outlets (6 per outlet, random,
excluding every headline already used in the earlier sets), (2) makes "distorted" copies by swapping one number, place or
verb for another, (3) adds invented headlines written for this purpose, (4) searches each headline with the same
GoogleNewsSearch class the application uses and saves what came back.

Nothing here decides anything: the rules in backend/app/ml/corroboration/check.py were fixed before this set was
collected, and evaluate_corroboration.py replays the saved results through that code. The feeds change by the hour, so a
re-run gives different headlines; the saved files are the record of what was measured.

Writes ai_models/evaluation/corroboration/<name>_sets.json and <name>_results.json (resumable); <name> defaults to "heldout".
The third set (23 Nov 2026) was made with:  collect_corroboration_data.py 23 fresh2 12 --no-invented
Usage: python ai_models/training/collect_corroboration_data.py [seed] [name] [per_outlet] [--no-invented]      (needs internet access)"""
from __future__ import annotations

import dataclasses
import json
import random
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.corroboration.news_search import GoogleNewsSearch, SearchUnavailable  # noqa: E402

OUT = ROOT / "ai_models" / "evaluation" / "corroboration"
FEEDS = {
    "dawn.com": "https://www.dawn.com/feeds/home", "bbc.com": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "aljazeera.com": "https://www.aljazeera.com/xml/rss/all.xml", "nytimes.com": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "theguardian.com": "https://www.theguardian.com/world/rss", "tribune.com.pk": "https://tribune.com.pk/feed/home",
    "thehindu.com": "https://www.thehindu.com/news/international/feeder/default.rss", "npr.org": "https://feeds.npr.org/1001/rss.xml",
}
SUBS = [("Karachi", "Lahore"), ("Lahore", "Karachi"), ("Pakistan", "India"), ("India", "Pakistan"), ("Iran", "Iraq"), ("Russia", "China"),
        ("Gaza", "Beirut"), ("Israel", "Egypt"), ("UK", "France"), ("France", "Spain"), ("Germany", "Italy"), ("killed", "rescued"),
        ("sentenced", "acquitted"), ("threatens", "welcomes"), ("rises", "falls"), ("falls", "rises"), ("wins", "loses"), ("loses", "wins"),
        ("approves", "rejects"), ("rejects", "approves"), ("bans", "allows"), ("arrested", "released")]
INVENTED = [
    "Government to give every household a free solar panel starting next week, ministry confirms",
    "Scientists announce that a daily glass of vinegar water reverses ageing within a month",
    "Supreme court abolishes all income tax for citizens earning under one million rupees a year",
    "Telecom regulator to block social media for the entire month of December, officials say",
    "Airline to cancel every international flight for a week after unexplained system failure, sources claim",
    "National cricket team to be dissolved after board announces surprise restructuring plan",
    "Health ministry declares seasonal flu vaccine mandatory for all adults from Monday",
    "Central bank to print new fifty thousand rupee note next month, insiders reveal",
    "Famous actor discovers ancient treasure worth billions during a film shoot, police confirm",
    "University announces that all exams are cancelled permanently and degrees will be awarded online",
    "Heavy rain to flood the capital for a full month, meteorological department warns in secret memo",
    "President to resign tonight after leaked recording, unnamed aides say",
]


def used_headlines() -> set[str]:
    seen: set[str] = set()
    for p in sorted(OUT.glob("*sets*.json")):
        if p.exists():
            seen |= {x["headline"] for x in json.loads(p.read_text(encoding="utf-8"))}
    return seen


def perturb(h: str):
    m = re.search(r"\b(\d[\d,\.]*)\b", h)
    if m and not re.match(r"^(19|20)\d\d$", m.group(1)):
        try:
            n = float(m.group(1).replace(",", ""))
            return h.replace(m.group(1), str(int(n * 3 + 7)) if n == int(n) else str(round(n * 3 + 7, 1)), 1), "number"
        except ValueError:
            pass
    for a, b in SUBS:
        if re.search(r"\b" + re.escape(a) + r"\b", h):
            return re.sub(r"\b" + re.escape(a) + r"\b", b, h, count=1), "swap:" + a
    return None, None


def build_set(seed: int, per_outlet: int = 6, invented: bool = True) -> list[dict]:
    random.seed(seed)
    seen, real = used_headlines(), []
    for dom, url in FEEDS.items():
        try:
            root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read())  # noqa: S310
        except Exception as exc:  # a feed that is down is skipped and said so
            print(dom, "skipped:", str(exc)[:80])
            continue
        titles = [(i.findtext("title") or "").strip() for i in root.iter("item")]
        titles = [t for t in titles if 35 <= len(t) <= 140 and t not in seen and not t.lower().startswith(("live", "watch", "podcast", "quiz"))]
        real += [{"outlet": dom, "headline": t} for t in random.sample(titles, min(per_outlet, len(titles)))]
    items = [{"id": f"H{i:02d}", "kind": "authentic", "headline": r["headline"], "own_outlet": r["outlet"]} for i, r in enumerate(real)]
    k = 0
    for r in real:
        p, how = perturb(r["headline"])
        if p and p != r["headline"]:
            items.append({"id": f"HD{k:02d}", "kind": "distorted", "headline": p, "own_outlet": None, "derived_from": r["headline"], "how": how})
            k += 1
    if invented:
        items += [{"id": f"HI{j:02d}", "kind": "invented", "headline": h, "own_outlet": None} for j, h in enumerate(INVENTED)]
    return items


def main(seed: int = 11, name: str = "heldout", per_outlet: int = 6, invented: bool = True) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sets_path, res_path = OUT / f"{name}_sets.json", OUT / f"{name}_results.json"
    if not sets_path.exists():
        sets_path.write_text(json.dumps(build_set(seed, per_outlet, invented), indent=1, ensure_ascii=False), encoding="utf-8")
    items = json.loads(sets_path.read_text(encoding="utf-8"))
    done = {x["id"]: x for x in json.loads(res_path.read_text(encoding="utf-8"))} if res_path.exists() else {}
    search = GoogleNewsSearch(timeout=25)
    for n, x in enumerate(items):
        if x["id"] in done and done[x["id"]].get("results") is not None:
            continue
        for attempt in range(4):
            try:
                x["results"] = [dataclasses.asdict(h) for h in search.search(x["headline"])]
                break
            except SearchUnavailable as exc:
                x["results"], x["error"] = None, str(exc)
                time.sleep(65)  # the provider pauses for 60 s after two HTTP 429 answers; wait that out
        done[x["id"]] = x
        res_path.write_text(json.dumps(list(done.values()), indent=1, ensure_ascii=False), encoding="utf-8")
        print(n, x["id"], len(x["results"] or []), flush=True)
        time.sleep(2.0)
    print("DONE")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(int(args[0]) if args else 11, args[1] if len(args) > 1 else "heldout", int(args[2]) if len(args) > 2 else 6, "--no-invented" not in sys.argv)
