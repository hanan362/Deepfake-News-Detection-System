"""What can honestly be said about the website an article came from.

There is no credibility score here, and an unfamiliar website is never called fake. The directory in
known_sources.json is small and hand-made; it holds well-known news organisations and sites that declare themselves
satire. The outcome is one of four statements: recognised news organisation, declared satire, resembles a recognised
site's address, or not enough information. The page-level signals are reported next to it as plain observations; most
are self-declared by the page (anyone can add an author line or a NewsArticle tag) so they never decide the outcome.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from app.ml.url_analysis.extract import Extracted

DIRECTORY_PATH = Path(__file__).with_name("known_sources.json")
TWO_PART_SUFFIXES = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.pk", "org.pk", "net.pk", "gov.pk", "edu.pk", "co.in", "org.in",
                     "com.au", "net.au", "org.au", "co.jp", "or.jp", "ne.jp", "co.nz", "com.br", "com.co", "co.za", "com.sg",
                     "com.hk", "com.tr", "com.cn", "com.mx", "co.id", "com.my", "com.bd", "com.lk"}
SHORTENERS = {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "buff.ly", "is.gd", "cutt.ly", "rb.gy", "shorturl.at", "lnkd.in", "fb.me"}
NOT_CHECKED = [
    "How old the domain is (no WHOIS or RDAP lookup is made).",
    "What fact-checking organisations have said about this website.",
    "Who owns or funds the website.",
    "Whether this particular article's claims are true.",
]
CAVEAT = ("This describes the website, not the article. Even a recognised publisher makes mistakes, and an unlisted "
          "website can be perfectly reliable.")
_HOMOGLYPHS = (("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("5", "s"))


@lru_cache
def directory() -> dict:
    return json.loads(DIRECTORY_PATH.read_text(encoding="utf-8"))


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").rstrip(".").lower()


def split_domain(host: str) -> tuple[str, str]:
    """(label, suffix) of a host. Uses a short list of two-part suffixes instead of the full public-suffix list, which
    is enough for matching against the directory and for the lookalike check."""
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in TWO_PART_SUFFIXES:
        return labels[-3], ".".join(labels[-2:])
    if len(labels) >= 2:
        return labels[-2], labels[-1]
    return host, ""


def _distance(a: str, b: str, limit: int) -> int:
    """Edit distance, giving up once it exceeds `limit`."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def _normalise(label: str) -> str:
    for a, b in _HOMOGLYPHS:
        label = label.replace(a, b)
    return label.replace("-", "")


def match_entry(host: str) -> dict | None:
    """The directory entry whose domain is this host or a parent of it (news.bbc.co.uk matches bbc.co.uk)."""
    best = None
    for e in directory()["entries"]:
        d = e["domain"]
        if host == d or host.endswith("." + d):
            if best is None or len(d) > len(best["domain"]):
                best = e
    return best


def find_lookalike(host: str) -> tuple[dict, str] | None:
    """An entry this host imitates, with the reason. Only called for hosts that are not listed themselves."""
    label, _suffix = split_domain(host)
    dotted = "." + host + "."
    entries = directory()["entries"]
    for e in entries:  # a listed domain placed in front of the real one: bbc.com.example.net
        if f".{e['domain']}." in dotted and not host.endswith("." + e["domain"]) and host != e["domain"]:
            return e, "It contains the name of a recognised website in front of its real domain."
    for e in entries:
        el, _ = split_domain(e["domain"])
        if len(el) >= 4 and _normalise(label) == _normalise(el) and label != el:
            return e, "Its name differs from a recognised website's only in look-alike characters."
    for e in entries:
        el, _ = split_domain(e["domain"])
        if len(el) >= 5 and label != el and _distance(label, el, 2 if len(el) >= 10 else 1) <= (2 if len(el) >= 10 else 1):
            return e, "Its name is one or two letters away from a recognised website's name."
    for e in entries:
        el, _ = split_domain(e["domain"])
        if len(el) >= 4 and label == el:
            return e, "It has the same name as a recognised website but a different ending."
    for e in entries:
        el, _ = split_domain(e["domain"])
        tokens = label.split("-")
        if len(el) >= 6 and label != el and (el in tokens or label.startswith(el) or label.endswith(el)):
            return e, "Its name is built around the name of a recognised website."
    return None


def _signal(sid: str, label: str, effect: str, detail: str) -> dict:
    return {"id": sid, "label": label, "effect": effect, "detail": detail}


def assess(requested_url: str, final_url: str, extracted: Extracted | None) -> dict:
    host = host_of(final_url)
    req_host = host_of(requested_url)
    entry = match_entry(host)
    lookalike = None if entry else find_lookalike(host)
    signals: list[dict] = []

    if final_url.lower().startswith("https://"):
        signals.append(_signal("https", "Secure connection", "supporting", "The page was delivered over https. Most sites, including bad ones, now use it."))
    else:
        signals.append(_signal("https", "No secure connection", "caution", "The page was delivered over plain http. Some older, legitimate sites still do this."))
    if req_host and split_domain(req_host)[0] != split_domain(host)[0]:
        kind = "a link shortener" if req_host in SHORTENERS else "another website"
        signals.append(_signal("redirect", "The address redirected", "neutral", f"The address you entered is on {kind} ({req_host}). The analysis used the page it led to, on {host}."))
    elif req_host in SHORTENERS:
        signals.append(_signal("shortener", "Link shortener", "neutral", "The address is a link shortener; the analysis used the page it led to."))
    if "xn--" in host:
        signals.append(_signal("idn", "Internationalised domain name", "neutral", "The domain uses non-Latin letters, which many legitimate sites do. Look closely for letters that imitate Latin ones."))
    if extracted is not None:
        if extracted.canonical_url:
            canon = host_of(extracted.canonical_url) or host
            if split_domain(canon) != split_domain(host):
                signals.append(_signal("canonical", "The page names another site as its original", "caution", f"Its canonical address is on {canon}. This page may be a copy of an article published there."))
        signals.append(_signal("author", "Author named" if extracted.author else "No author found", "supporting" if extracted.author else "neutral",
                               "The page names an author (self-declared)." if extracted.author else "No author was found in the page's metadata. Many legitimate pages leave it out."))
        signals.append(_signal("date", "Publication date found" if extracted.published else "No publication date found", "supporting" if extracted.published else "neutral",
                               f"Declared date: {extracted.published}." if extracted.published else "No date was found in the page's metadata."))
        signals.append(_signal("article_markup", "Declares itself an article" if extracted.declares_article else "No article markup",
                               "supporting" if extracted.declares_article else "neutral",
                               "Structured data or og:type says this is an article (self-declared; anyone can add it)." if extracted.declares_article
                               else "No NewsArticle structured data was found. Many legitimate pages have none."))

    d = directory()
    base = {"host": host, "signals": signals, "not_checked": NOT_CHECKED, "caveat": CAVEAT,
            "directory": {"version": d["version"], "entries": len(d["entries"]), "meaning": d["meaning"]},
            "matched": None, "resembles": None}
    if entry and entry["category"] == "satire":
        return {**base, "assessment": "declared_satire", "label": "Declared satire",
                "summary": f"{entry['name']} publishes satire. Its stories are jokes, not reporting, so a writing-style result for them says nothing about misinformation.",
                "matched": entry}
    if entry:
        return {**base, "assessment": "recognised_publisher", "label": "Recognised news organisation",
                "summary": f"{host} belongs to {entry['name']}, a well-known news organisation. That says nothing about whether this particular article is accurate.",
                "matched": entry}
    if lookalike:
        e, why = lookalike
        return {**base, "assessment": "lookalike", "label": "Address resembles a recognised website",
                "summary": f"{host} is not {e['domain']} ({e['name']}). {why} This may be a coincidence; check that you are on the website you meant. It is not evidence that the content is false.",
                "resembles": {**e, "reason": why}}
    return {**base, "assessment": "unknown", "label": "Not enough information",
            "summary": f"{host} is not in the project's small directory of recognised news organisations, so there is not enough information to rate it. That does not mean it is unreliable: most local and specialist outlets are not listed."}
