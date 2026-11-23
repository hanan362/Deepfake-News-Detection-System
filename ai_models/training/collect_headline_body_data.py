"""Collects REAL articles (headline from the outlet's RSS feed, lead of the article text from the article page) for testing the
headline-against-text check. Nothing here decides anything: it only saves what the outlets published, with the address, so that the
measurement in evaluate_headline_body.py can be repeated. The article texts belong to their outlets; the saved file is a test
fixture for this project and not a dataset it redistributes (delete it if that is a concern; only the evaluation script uses it).

Each article text is read with the same extractor the application uses for web addresses (app.ml.url_analysis.extract). The
first 250 words are saved as "body" (the part where an article states what its headline says) and the whole text, cut at the
application's own limit of 50,000 characters, as "full": the application compares a headline with the whole text it is given, so the
measurement of a later set uses "full". The first two sets only have "body"; "python collect_headline_body_data.py backfill <name>"
adds "full" to a set by reading its pages again.

Usage: python ai_models/training/collect_headline_body_data.py [seed] [per_outlet] [name] [sections]      (needs internet access)
With "sections" the feeds of other sections of each outlet (business, technology, science, health, sport, UK/national news) are used
as well as the world feeds, so that a later set is not limited to the stories of the world news pages.
Writes ai_models/evaluation/headline_body/<name>.json (default "articles"; resumable). An article already saved in any other
file of that folder is not collected again, so two sets never share an article."""
from __future__ import annotations

import json
import random
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.url_analysis.extract import decode_html, extract  # noqa: E402

OUT = ROOT / "ai_models" / "evaluation" / "headline_body"
FEEDS = {
    "bbc.com": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "aljazeera.com": "https://www.aljazeera.com/xml/rss/all.xml", "theguardian.com": "https://www.theguardian.com/world/rss", "tribune.com.pk": "https://tribune.com.pk/feed/home",
    "thehindu.com": "https://www.thehindu.com/news/international/feeder/default.rss",
}
SECTION_FEEDS = {
    "bbc.com": ["https://feeds.bbci.co.uk/news/business/rss.xml", "https://feeds.bbci.co.uk/news/technology/rss.xml",
                "https://feeds.bbci.co.uk/news/health/rss.xml", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
                "https://feeds.bbci.co.uk/news/uk/rss.xml"],
    "theguardian.com": ["https://www.theguardian.com/uk-news/rss", "https://www.theguardian.com/business/rss",
                        "https://www.theguardian.com/technology/rss", "https://www.theguardian.com/science/rss",
                        "https://www.theguardian.com/us-news/rss", "https://www.theguardian.com/environment/rss"],
    "thehindu.com": ["https://www.thehindu.com/news/national/feeder/default.rss", "https://www.thehindu.com/business/feeder/default.rss",
                     "https://www.thehindu.com/sci-tech/feeder/default.rss", "https://www.thehindu.com/sport/feeder/default.rss"],
    "tribune.com.pk": ["https://tribune.com.pk/feed/pakistan", "https://tribune.com.pk/feed/business", "https://tribune.com.pk/feed/world"],
    "aljazeera.com": [],
}
LEAD_WORDS = 250
MAX_TEXT_CHARS = 50_000
MIN_BODY_WORDS = 120
UA = {"User-Agent": "Mozilla/5.0"}


def lead(text: str) -> str:
    out, n = [], 0
    for para in text.split("\n\n"):
        w = len(para.split())
        if n and n + w > LEAD_WORDS:
            break
        out.append(para)
        n += w
    return "\n\n".join(out)


def main(seed: int = 5, per_outlet: int = 14, name: str = "articles", sections: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    have = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    seen = {a["url"] for a in have}
    for other in OUT.glob("*.json"):
        if other != path and other.name.startswith(("articles", "test")):
            seen |= {a["url"] for a in json.loads(other.read_text(encoding="utf-8"))}
    random.seed(seed)
    for dom, feed in FEEDS.items():
        if sum(a["outlet"] == dom for a in have) >= per_outlet:
            continue
        items = []
        for url_feed in [feed] + (SECTION_FEEDS.get(dom, []) if sections else []):
            try:
                root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(url_feed, headers=UA), timeout=25).read())  # noqa: S310
            except Exception as exc:
                print(dom, "feed skipped:", url_feed[-40:], str(exc)[:60])
                continue
            items += [((i.findtext("title") or "").strip(), (i.findtext("link") or "").strip()) for i in root.iter("item")]
        items = [(t, u) for t, u in items if 35 <= len(t) <= 140 and u and u not in seen
                 and not t.lower().startswith(("live", "watch", "podcast", "quiz", "video", "in pictures"))]
        random.shuffle(items)
        got = 0
        for title, url in items:
            if got >= per_outlet:
                break
            try:
                resp = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25)  # noqa: S310
                html = decode_html(resp.read(3_000_000), resp.headers.get_content_charset())
                page = extract(html)
            except Exception as exc:
                print("  skipped", url[:70], str(exc)[:50])
                continue
            if page.word_count < MIN_BODY_WORDS:
                continue
            have.append({"id": f"{name[0].upper()}{len(have):03d}", "outlet": dom, "headline": title, "url": url, "body": lead(page.text), "full": page.text[:MAX_TEXT_CHARS],
                         "page_words": page.word_count})
            seen.add(url)
            got += 1
            path.write_text(json.dumps(have, indent=1, ensure_ascii=False), encoding="utf-8")
            print(dom, got, title[:70], flush=True)
            time.sleep(1.0)
    print("DONE", len(have), "articles")


def backfill(name: str) -> None:
    """Adds "full" (the whole text, as the application would read the page) to the articles of a saved set that lack it."""
    path = OUT / f"{name}.json"
    have = json.loads(path.read_text(encoding="utf-8"))
    for a in have:
        if a.get("full"):
            continue
        try:
            resp = urllib.request.urlopen(urllib.request.Request(a["url"], headers=UA), timeout=25)  # noqa: S310
            page = extract(decode_html(resp.read(3_000_000), resp.headers.get_content_charset()))
            a["full"] = page.text[:MAX_TEXT_CHARS]
        except Exception as exc:
            print("  not read again", a["id"], str(exc)[:60])
        time.sleep(0.5)
    path.write_text(json.dumps(have, indent=1, ensure_ascii=False), encoding="utf-8")
    print("DONE", sum(bool(a.get("full")) for a in have), "of", len(have), "have the full text")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "backfill":
        backfill(sys.argv[2])
        raise SystemExit
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5, int(sys.argv[2]) if len(sys.argv) > 2 else 14, sys.argv[3] if len(sys.argv) > 3 else "articles",
         len(sys.argv) > 4 and sys.argv[4] == "sections")
