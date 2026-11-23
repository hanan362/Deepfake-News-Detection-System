"""Turn retrieved evidence into a cautious verdict for one claim.

Rules, all visible in the result:
* An evidence passage only counts when it is about the claim: its words must overlap the claim's (RELEVANCE_MIN).
* A stance (supports / contradicts) needs the NLI model to be at least STANCE_THRESHOLD sure for one sentence of it.
* Supported = at least one supporting passage and no contradicting one. Contradicted = the reverse. Both = Mixed.
* Everything else, including "nothing found", an unreachable provider and a missing NLI model, is Insufficient Evidence.
Published fact-checks are listed with the rating their publisher gave. The system does not translate those ratings."""
from __future__ import annotations

import re
from typing import Any

from app.ml.fact_checking.claims import split_sentences
from app.ml.fact_checking.nli import NliModel
from app.ml.fact_checking.providers import Evidence, Provider, ProviderResult, content_words

STANCE_THRESHOLD = 0.85
RELEVANCE_MIN = 0.25
SENTENCES_PER_PASSAGE = 1

SUPPORTED, CONTRADICTED, MIXED, INSUFFICIENT = "Supported", "Contradicted", "Mixed Evidence", "Insufficient Evidence"


def relevance(claim: str, passage: str) -> float:
    """Share of the claim's content words that appear in the passage (lexical overlap, not semantic similarity)."""
    c = set(content_words(claim))
    return round(len(c & set(content_words(passage))) / len(c), 3) if c else 0.0


def _top_sentences(claim: str, passage: str, n: int, title: str = "") -> list[str]:
    cw = set(content_words(claim))
    sents = [name_the_subject(s, title) if title else s for s in split_sentences(passage) if len(s.split()) >= 3]
    return sorted(sents, key=lambda s: -len(cw & set(content_words(s))))[:n]


# Wikipedia's first sentence often carries a pronunciation in brackets: "The Eiffel Tower ( EYE-fəl; French: Tour Eiffel [tuʁ ɛfɛl] ) is ...".
# The inference model read that sentence as contradicting "The Eiffel Tower is located in Paris, France" (99.9%); without the bracket
# the same sentence is read as supporting it (60%). Only brackets that hold pronunciation symbols are removed.
_PRONUNCIATION = re.compile(r"\s*\([^()]*[\u0250-\u02ff\u1d00-\u1dbf][^()]*\)")
_QUALIFIED_TITLE = re.compile(r"^(?P<base>.+?)\s*\((?P<qualifier>[^()]+)\)$")


def strip_pronunciation(text: str) -> str:
    return " ".join(_PRONUNCIATION.sub("", text).split())


def namesake_titles(titles: list[str], claim: str) -> set[str]:
    """Wikipedia puts a bracket after the title of a page about something else that shares a name: "Eiffel Tower (Paris, Texas)"
    next to "Eiffel Tower". When both pages were found, the bracketed one is about another subject, unless the claim itself
    names what the bracket says. Such a page is listed but does not count for or against the claim."""
    plain = {t.lower() for t in titles if not _QUALIFIED_TITLE.match(t)}
    claim_words = set(content_words(claim))
    out: set[str] = set()
    for t in titles:
        m = _QUALIFIED_TITLE.match(t)
        if m and m["base"].lower() in plain and not set(content_words(m["qualifier"])) <= claim_words:
            out.add(t)
    return out


# Wikipedia introductions name their subject once and then say "She shared the 1903 Nobel Prize in Physics ...". A sentence taken
# out of its paragraph loses that reference, and the inference model cannot tell who "she" is. A pronoun that starts a sentence is
# replaced by the page title, which is the subject of the page. This is a heuristic: it is wrong when the pronoun points elsewhere.
_LEADING_PRONOUN = re.compile(r"^(?:He|She|It|They)\b")
_LEADING_POSSESSIVE = re.compile(r"^(?:His|Her|Its|Their)\b")


def name_the_subject(sentence: str, title: str) -> str:
    subject = (_QUALIFIED_TITLE.match(title)["base"] if _QUALIFIED_TITLE.match(title) else title).strip()
    if not subject:
        return sentence
    if _LEADING_PRONOUN.match(sentence):
        return subject + sentence[_LEADING_PRONOUN.match(sentence).end():]
    if _LEADING_POSSESSIVE.match(sentence):
        return subject + "'s" + sentence[_LEADING_POSSESSIVE.match(sentence).end():]
    return sentence


def verify_claim(claim: str, providers: list[Provider], nli: NliModel) -> dict[str, Any]:
    results: list[ProviderResult] = [p.search(claim) for p in providers]
    stance_available = nli.available
    items: list[dict[str, Any]] = []
    namesakes = namesake_titles([ev.title for res in results for ev in res.evidence if ev.kind == "encyclopedia"], claim)
    for res in results:
        for ev in res.evidence:
            rel = relevance(claim, f"{ev.title}. {ev.text}")
            item: dict[str, Any] = {
                "provider": ev.provider, "kind": ev.kind, "title": ev.title, "url": ev.url, "published": ev.published,
                "rating": ev.rating, "publisher": ev.publisher, "relevance": rel, "excerpt": re.sub(r"\s+", " ", ev.text)[:400],
                "stance": "not_assessed", "stance_probabilities": None, "best_sentence": None,
            }
            if ev.kind == "fact_check":
                item["stance"] = "published_rating"  # reported as published; never converted into our own stance
            elif ev.title in namesakes:
                item["stance"] = "other_subject"  # same name, different subject: not used as evidence for or against
            elif rel < RELEVANCE_MIN:
                item["stance"] = "not_relevant"
            elif stance_available:
                sentences = _top_sentences(claim, strip_pronunciation(ev.text), SENTENCES_PER_PASSAGE, ev.title)
                scored = nli.predict([(s, claim) for s in sentences]) if sentences else []
                best = max(zip(sentences, scored), key=lambda t: max(t[1]["entailment"], t[1]["contradiction"]), default=None)
                if best:
                    sent, probs = best
                    item["best_sentence"], item["stance_probabilities"] = sent, probs
                    if probs["entailment"] >= STANCE_THRESHOLD:
                        item["stance"] = "supports"
                    elif probs["contradiction"] >= STANCE_THRESHOLD:
                        item["stance"] = "contradicts"
                    else:
                        item["stance"] = "unclear"
                else:
                    item["stance"] = "unclear"
            items.append(item)

    supports = [i for i in items if i["stance"] == "supports"]
    contradicts = [i for i in items if i["stance"] == "contradicts"]
    if supports and contradicts:
        verdict, why = MIXED, "Some passages support the claim and others contradict it."
    elif supports:
        verdict, why = SUPPORTED, f"{len(supports)} relevant passage(s) support the claim and none contradict it."
    elif contradicts:
        verdict, why = CONTRADICTED, f"{len(contradicts)} relevant passage(s) contradict the claim and none support it."
    else:
        reasons = []
        encyclopedic = [i for i in items if i["kind"] == "encyclopedia"]
        assessed = [i for i in encyclopedic if i["stance"] in ("unclear", "supports", "contradicts")]
        if not items:
            reasons.append("No evidence was found.")
        elif encyclopedic and not stance_available:
            reasons.append("Evidence was found, but the language-inference model is not available, so its stance was not judged.")
        elif assessed:
            reasons.append(f"No passage supported or contradicted the claim with at least {STANCE_THRESHOLD:.0%} certainty.")
        elif encyclopedic:
            reasons.append("The pages found are not clearly about this claim.")
        elif items:
            reasons.append("Only published fact-checks were found. Their ratings are listed, but they are not turned into a verdict here.")
        if any(r.status in ("error", "not_configured") for r in results):
            reasons.append("At least one source could not be searched (see the sources list).")
        verdict, why = INSUFFICIENT, " ".join(reasons) or "No relevant evidence."
    return {
        "claim": claim, "verdict": verdict, "reason": why, "evidence": items,
        "providers": [{"provider": r.provider, "status": r.status, "message": r.message, "count": len(r.evidence)} for r in results],
        "stance_model": nli.model_id if stance_available else None,
        "rules": {"stance_threshold": STANCE_THRESHOLD, "relevance_min": RELEVANCE_MIN,
                  "prepared_text": "Pronunciation guides in brackets are removed and a leading pronoun is replaced by the page title before a sentence is judged."},
    }


def overall_verdict(claims: list[dict[str, Any]]) -> str:
    verdicts = {c["verdict"] for c in claims}
    if not claims or verdicts == {INSUFFICIENT}:
        return INSUFFICIENT
    if MIXED in verdicts or (SUPPORTED in verdicts and CONTRADICTED in verdicts):
        return MIXED
    if CONTRADICTED in verdicts:
        return CONTRADICTED
    return SUPPORTED
