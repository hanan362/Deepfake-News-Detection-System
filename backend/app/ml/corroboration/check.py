"""Do listed news organisations report the same story?

The check takes a headline, finds recent headlines on the same subject, keeps only those from organisations named in the
hand-made directory of well-known outlets (satire sites excluded), and asks a natural-language-inference model whether
each such headline says what the user's headline says. It compares headlines only, never article bodies.

Rules (fixed before the evaluation in ai_models/evaluation/results/corroboration.json was read as a whole; see
docs/technical_documentation/ai_model_documentation.md for how they were chosen and what they cost):
  Corroborated: a listed outlet's headline shares at least half of the headline's content words and the model is at least
                60% sure it entails it.
  Disputed:     no outlet corroborates, but a listed outlet's headline shares at least 70% of the content words and the
                model is at least 80% sure it contradicts it. This is shown as a difference to look at, never as a ruling.
  Not found:    anything else. This says nothing against the headline. When nothing matched, listed outlets' headlines that
                share at least 30% of the content words are shown as "related" (one per outlet, at most three). They are
                shown for the reader to look at; they never change the verdict and say nothing about whether the headline is true.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.ml.corroboration.news_search import NewsHit, NewsSearch, SearchUnavailable, host_of
from app.ml.url_analysis.source import match_entry

logger = logging.getLogger(__name__)

SUPPORT_OVERLAP = 0.5
SUPPORT_ENTAILMENT = 0.6
CONTRADICT_OVERLAP = 0.7
CONTRADICT_PROBABILITY = 0.8
MIN_WORDS = 5
MAX_QUERY_CHARS = 200
MAX_OUTLETS_SHOWN = 5
ENTITY_GUARD = True   # a number or name in the user's headline must also appear in the headline that is said to confirm it
RELATED_OVERLAP = 0.3
MAX_RELATED_SHOWN = 3

RULES = {
    "compares": "headlines only, not article text",
    "corroborated": f"a listed outlet's headline shares at least {int(SUPPORT_OVERLAP * 100)}% of the headline's content words and the "
                    f"inference model is at least {int(SUPPORT_ENTAILMENT * 100)}% sure it says the same",
    "disputed": f"no outlet corroborates, and a listed outlet's headline shares at least {int(CONTRADICT_OVERLAP * 100)}% of the content "
                f"words while the model is at least {int(CONTRADICT_PROBABILITY * 100)}% sure it says the opposite",
    "not_found": "anything else; this says nothing against the headline",
    "related": f"when nothing matches, headlines of listed outlets that share at least {int(RELATED_OVERLAP * 100)}% of the content words are "
               "listed as related coverage; they are for the reader to look at and never change the verdict",
}
LIMITS = (
    "Only the headline is compared, not the article. Only outlets named in the project's small hand-made directory count; an "
    "outlet that is not listed is ignored, and a story that no listed outlet has run (local news, very new news, or old news, which "
    "this search rarely returns) comes out as Not found, which says nothing against it. A headline that was copied from a real "
    "outlet with a changed article body would still be corroborated. The headline is sent to Google News search (an unofficial feed)."
)

_STOP = set("a an the of to in on at for from by with and or but is are was were be been being as that this these those it its into over "
            "after before about than then their his her they he she we you i not no new says say said will would could can may might has "
            "have had do does did up out off per amid".split())


def _stem(w: str) -> str:
    return re.sub(r"(ing|ed|es|s)$", "", w) if len(w) > 4 else w


def content_words(text: str) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 1}


def overlap(headline: str, other: str) -> float:
    """The share of the headline's content words that also appear in the other headline."""
    mine = content_words(headline)
    return len(mine & content_words(other)) / max(1, len(mine))


def _tokens(text: str) -> list[str]:
    return [t.strip(".'\u2019-").replace(".", "") for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019.\-]*", text)]


def specifics(text: str) -> set[str]:
    """The numbers and the capitalised words (names, places) of a headline, lower-cased and stemmed. The first word counts unless it
    is an everyday function word ("The", "After"). A headline written in Title Case, where nearly every word is capitalised, contributes
    its numbers only, because there a capital says nothing."""
    toks = [t for t in _tokens(text) if t]
    words = [t for t in toks if len(t) > 3]
    title_case = len(words) >= 4 and sum(t[0].isupper() for t in words) / len(words) >= 0.6
    out: set[str] = set()
    for i, t in enumerate(toks):
        if any(c.isdigit() for c in t) or (not title_case and t[0].isupper() and (i > 0 or t.lower() not in _STOP)):
            out.add(_stem(t.lower()))
    return out


def missing_specifics(headline: str, other: str) -> set[str]:
    """Numbers and names in the user's headline that the other headline does not contain. The inference model sometimes reads "Iraq" for
    "Iran", or one number for another, as the same statement; this rule does not. Chosen after one such failure (fresh set, 23 Nov
    2026), so it is a coarse safeguard that was checked on all sets, not a tuned component: see the documentation for what it cost."""
    have = {_stem(t.lower()) for t in _tokens(other) if t}
    return {w for w in specifics(headline) if w not in have}


def clean_query(headline: str | None) -> str | None:
    """The headline as it will be searched: one line, without a trailing site name ("Title | Site"), at most 200 characters."""
    if not headline:
        return None
    text = " ".join(headline.split())
    parts = re.split(r"\s+[|–—]\s+|\s+-\s+", text)
    if len(parts) > 1 and len(parts[0].split()) >= 3:
        text = parts[0]
    return text[:MAX_QUERY_CHARS].strip() or None


def _result(status: str, query: str | None, *, reason: str | None = None, message: str | None = None, outlets: list | None = None,
            searched: int = 0, listed: int = 0, provider: str | None = None, excluded: str | None = None,
            related: list | None = None) -> dict[str, Any]:
    return {"status": status, "reason": reason, "message": message, "query": query, "outlets": outlets or [], "related": related or [],
            "results_read": searched, "listed_outlet_results": listed, "excluded_outlet": excluded, "provider": provider, "rules": RULES,
            "limits": LIMITS}


def skipped(reason: str, message: str, query: str | None = None) -> dict[str, Any]:
    return _result("skipped", query, reason=reason, message=message)


def corroborate(headline: str | None, provider: NewsSearch, nli, exclude_outlet: str | None = None) -> dict[str, Any]:
    """Run the check. Never raises: a problem becomes status 'unavailable' with a reason.

    exclude_outlet: the organisation the article itself came from (when a web address was analysed). Its own report of its own
    headline proves nothing, so it is not counted."""
    query = clean_query(headline)
    if not query:
        return skipped("no_headline", "No headline was given, so no news search was made. Add the headline to compare it with news reports.")
    if len(query.split()) < MIN_WORDS:
        return skipped("too_short", f"A headline of fewer than {MIN_WORDS} words is too vague to search for.", query)
    try:
        hits = provider.search(query)
    except SearchUnavailable as exc:
        return _result("unavailable", query, reason="search_failed", message=str(exc), provider=provider.name)
    except Exception:  # a provider fault must never fail the analysis
        logger.exception("News search failed")
        return _result("unavailable", query, reason="search_failed", message="The news search failed.", provider=provider.name)

    listed: list[tuple[NewsHit, dict, float]] = []
    for hit in hits:
        entry = match_entry(host_of(hit.site_url)) if hit.site_url else None
        if entry and entry.get("category") != "satire" and entry["name"] != exclude_outlet:
            listed.append((hit, entry, overlap(query, hit.title)))
    candidates = [(h, e, ov) for h, e, ov in listed if ov >= SUPPORT_OVERLAP]
    # The inference model (slow to load the first time) is needed only when some listed outlet's headline is close enough to compare.
    if candidates and not getattr(nli, "available", False):
        return _result("unavailable", query, reason="model_missing", provider=provider.name, searched=len(hits), listed=len(listed),
                       excluded=exclude_outlet,
                       message="The inference model is not installed, so the headlines found could not be compared with this one.")
    try:
        scores = nli.predict([(h.title, query) for h, _e, _ov in candidates]) if candidates else []
    except Exception:
        logger.exception("Headline comparison failed")
        return _result("unavailable", query, reason="model_failed", message="The inference model could not compare the headlines.",
                       provider=provider.name, searched=len(hits), listed=len(listed), excluded=exclude_outlet)

    same: dict[str, dict] = {}
    different: dict[str, dict] = {}
    for (hit, entry, ov), p in zip(candidates, scores):
        row = {"name": entry["name"], "title": hit.title, "url": hit.link, "published": hit.published, "overlap": round(ov, 2),
               "entailment": round(p.get("entailment", 0.0), 2), "contradiction": round(p.get("contradiction", 0.0), 2)}
        if p.get("entailment", 0.0) >= SUPPORT_ENTAILMENT and not (ENTITY_GUARD and missing_specifics(query, hit.title)):
            same.setdefault(entry["name"], {**row, "relation": "same_story"})
        elif ov >= CONTRADICT_OVERLAP and p.get("contradiction", 0.0) >= CONTRADICT_PROBABILITY:
            different.setdefault(entry["name"], {**row, "relation": "different_report"})
    common = dict(searched=len(hits), listed=len(listed), provider=provider.name, excluded=exclude_outlet)
    if same:
        n = len(same)
        return _result("corroborated", query, outlets=list(same.values())[:MAX_OUTLETS_SHOWN], **common,
                       message=f"The headline matches a report by {n} listed news organisation{'s' if n != 1 else ''}: {', '.join(same)}.")
    if different:
        return _result("disputed", query, outlets=list(different.values())[:MAX_OUTLETS_SHOWN], **common,
                       message="A listed news organisation reports something different under a very similar headline. Read it before relying on this one.")
    related: dict[str, dict] = {}
    for hit, entry, ov in sorted(listed, key=lambda t: -t[2]):
        if ov >= RELATED_OVERLAP and entry["name"] not in related:
            related[entry["name"]] = {"name": entry["name"], "title": hit.title, "url": hit.link, "published": hit.published, "overlap": round(ov, 2)}
    return _result("not_found", query, **common, related=list(related.values())[:MAX_RELATED_SHOWN],
                   message="No listed news organisation was found with a matching headline. This does not mean the story is false: it may be local, very new or old.")


# ---- how the result changes the verdict -------------------------------------------------------------------------

_COMBINABLE = {"low_confidence", "too_short", "model_leans_real", "model_leans_fake"}


def combine(result: dict[str, Any], corr: dict[str, Any]) -> dict[str, Any]:
    """The text result after the corroboration check. It only ever moves towards caution, except that a corroborated headline
    turns an undecided reading into 'Likely Real'. 'Disputed' is never turned into 'Likely Fake'.

      reading            corroborated                disputed
      Unverified         Likely Real (corroborated)  Unverified
      Likely Real        Likely Real                 Unverified (disputed)
      Likely Fake        Unverified (signals differ) Likely Fake
    """
    status = corr.get("status")
    reason = result.get("reason")
    if reason not in _COMBINABLE or status not in ("corroborated", "disputed"):
        return result
    verdict = result["verdict"]
    if status == "corroborated":
        if verdict == "Unverified":
            return {**result, "verdict": "Likely Real", "confidence": None, "reason": "corroborated",
                    "message": corr["message"] + " The writing-style reading was undecided."}
        if verdict == "Likely Fake":
            return {**result, "verdict": "Unverified", "confidence": None, "reason": "signals_differ",
                    "message": "The writing resembles articles labelled fake, but the headline matches a report by a listed outlet. "
                               "The two readings disagree, so no call is made."}
        return result
    if verdict == "Likely Real":
        return {**result, "verdict": "Unverified", "confidence": None, "reason": "disputed", "message": corr["message"]}
    return result


def combine_publisher(result: dict[str, Any], source: dict[str, Any], corr: dict[str, Any] | None = None) -> dict[str, Any]:
    """The result of a web address after the website assessment. Applied only to a result that nothing else has changed.

    A page that was actually served from the website of a listed news organisation was published by it: nobody else can put a
    page there. That shows who published the article, never that what it says is accurate. Rule, mirroring combine():
      Unverified   -> Likely Real (published by a listed outlet)
      Likely Real  -> unchanged
      Likely Fake  -> Unverified (the readings differ)
    Not applied to satire sites (they get no verdict at all), to unfamiliar sites, to look-alike addresses, to pages whose
    text could not be read, or when another listed outlet reports something different under a very similar headline.
    """
    matched = source.get("matched") if source.get("assessment") == "recognised_publisher" else None
    if not matched or result.get("reason") not in _COMBINABLE or (corr or {}).get("status") == "disputed":
        return result
    name = matched["name"]
    if result["verdict"] == "Unverified":
        return {**result, "verdict": "Likely Real", "confidence": None, "reason": "published_by_listed_outlet",
                "message": f"This page is on the website of {name}, a listed news organisation. That shows who published it, not that what "
                           "it says is accurate. The writing-style reading was undecided."}
    if result["verdict"] == "Likely Fake":
        return {**result, "verdict": "Unverified", "confidence": None, "reason": "signals_differ",
                "message": f"The writing resembles articles labelled fake, but the page is on the website of {name}, a listed news "
                           "organisation. The two readings disagree, so no call is made."}
    return result
