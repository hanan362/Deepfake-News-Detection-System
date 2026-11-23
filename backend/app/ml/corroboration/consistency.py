"""Does the article text say what its headline says?

A headline can be real while the text under it is not: someone copies a real outlet's headline and writes something else below
it. The headline comparison in check.py cannot see that, because it never reads the text. This check reads both. It takes the
first sentences of the text (where an article states what its headline says), asks a natural-language-inference model whether
the text entails the headline, and compares the numbers and names of the headline with the text.

It sends nothing out: it runs on the server with the same inference model as the evidence check.

Rules (set before the measurement in ai_models/evaluation/results/headline_body.json; the thresholds were looked at on a first
set of articles and then frozen and measured on later sets, see docs/technical_documentation/ai_model_documentation.md):
  Consistent:        a window of one or two of the first sentences entails the headline (model at least 60% sure), and every number
                     and name of the headline appears in the text.
  Contradicts:       not consistent, and a window that shares at least half of the headline's content words is judged by the
                     model, with at least 80% certainty, to say the opposite. A headline that is a question is not judged: it
                     claims nothing that a text could contradict.
  Unrelated:         under a quarter of the headline's content words appear anywhere in the part of the text that was read.
  Different details: the text is about the same subject (at least half of the content words appear) but a number or name of the
                     headline does not appear in it. Years are not compared. The first word of a headline is a name only if it is
                     not an ordinary English word (it is capitalised only because it begins the headline).
  Not stated:        anything else: the text is about the subject but its first sentences do not state the headline.
A result other than "consistent" never makes a verdict "Likely Fake". It only stops "Likely Real" (see combine_text_match).

What it cannot see: a text that agrees with its headline and then adds false details further on. That reads as consistent.
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.ml.corroboration.check import _STOP, _stem, content_words
from app.ml.fact_checking.claims import split_sentences

logger = logging.getLogger(__name__)

LEAD_SENTENCES = 10          # how much of the text is read: the first ten sentences
MIN_HEADLINE_WORDS = 4
MIN_TEXT_WORDS = 30
SUPPORT_ENTAILMENT = 0.6
CONTRADICT_PROBABILITY = 0.8
CONTRADICT_OVERLAP = 0.5
UNRELATED_OVERLAP = 0.25
SAME_SUBJECT_OVERLAP = 0.5
MAX_WINDOW_WORDS = 90
REPEAT_OVERLAP = 0.9         # a sentence that only repeats the headline is not evidence of anything

RULES = {
    "reads": f"the first {LEAD_SENTENCES} sentences of the text, in windows of one or two sentences, against the headline",
    "consistent": f"a window entails the headline (model at least {int(SUPPORT_ENTAILMENT * 100)}% sure) and every number and name of the "
                  "headline appears in the text",
    "contradicts": f"a window sharing at least {int(CONTRADICT_OVERLAP * 100)}% of the headline's content words is judged, with at least "
                   f"{int(CONTRADICT_PROBABILITY * 100)}% certainty, to say the opposite (a headline that is a question is not judged)",
    "unrelated": f"fewer than {int(UNRELATED_OVERLAP * 100)}% of the headline's content words appear in the part of the text that was read",
    "details_differ": f"at least {int(SAME_SUBJECT_OVERLAP * 100)}% of the content words appear, but a number or name of the headline appears "
                      "nowhere in the text (years are not compared, and a first word that is an ordinary English word is not a name)",
    "not_stated": "anything else: the text is about the subject but its first sentences do not state what the headline says",
}
LIMITS = (
    "Only the first sentences of the text are read, and only against the headline. A text that agrees with its headline and then adds "
    "false details further on reads as consistent, and so does a true text under a headline that only roughly summarises it may read "
    "as not stated. The check says nothing about whether either is true. It works for English only, and it needs a text of at least "
    f"{MIN_TEXT_WORDS} words."
)

_NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
                 "ten": "10", "eleven": "11", "twelve": "12", "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
                 "hundred": "100"}
_ALIASES = [(re.compile(p, re.I), r) for p, r in (
    (r"\bU\.S\.A?\.?|\bUSA\b|\bUnited States(?: of America)?\b", "US"), (r"\bU\.K\.?|\bUnited Kingdom\b", "UK"),
    (r"\bEuropean Union\b", "EU"), (r"\bUnited Nations\b", "UN"), (r"\bGovt\.?(?=\W|$)", "government"),
    (r"\bPM\b", "prime minister"))]
# "$200m", "200 million", "1.5bn", "3 billion": one number, so that the two spellings of an amount are the same
_QUANTITY = re.compile(r"[$\u00a3\u20ac]?(\d[\d,]*(?:\.\d+)?)\s?(thousand|million|billion|mn|bn|m|b|k)\b", re.I)
_SCALE = {"thousand": 1e3, "k": 1e3, "million": 1e6, "mn": 1e6, "m": 1e6, "billion": 1e9, "bn": 1e9, "b": 1e9}
_DIGITS_NUMBER = re.compile(r"(?<![\w.])(\d[\d,]*)(?:\.\d+)?(?![\w])")
PREFIX = 5   # two words that start with the same five letters count as the same ("Nigeria", "Nigerian"; "Korea", "Korean")


def _normalise(text: str) -> str:
    """Spellings that mean the same thing are made equal, so that "Five" matches "5" and "U.S." matches "United States"; possessives
    ("China's") and hyphens ("Ebola-hit") are dropped."""
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = re.sub(r"'s\b", "", text)
    text = text.replace("-", " ")
    for pattern, repl in _ALIASES:
        text = pattern.sub(repl, text)
    text = re.sub(r"\b(" + "|".join(_NUMBER_WORDS) + r")\b", lambda m: _NUMBER_WORDS[m.group(1).lower()], text, flags=re.I)
    text = _QUANTITY.sub(lambda m: str(round(float(m.group(1).replace(",", "")) * _SCALE[m.group(2).lower()])), text)
    return _DIGITS_NUMBER.sub(lambda m: m.group(1).replace(",", ""), text)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", text)


def _same(a: str, b: str) -> bool:
    return a == b or (len(a) >= PREFIX and len(b) >= PREFIX and a[:PREFIX] == b[:PREFIX])


def overlap(headline: str, other: str) -> float:
    """The share of the headline's content words that appear in the other text (a word also counts when it starts with the same
    five letters as one of the other text's words)."""
    mine = content_words(headline)
    theirs = content_words(other)
    return sum(any(_same(w, t) for t in theirs) for w in mine) / max(1, len(mine))


_WORDS_FILE = Path(__file__).with_name("ordinary_words.txt")
_SUFFIXES = (("ies", "y"), ("ied", "y"), ("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("es", ""), ("s", ""), ("d", ""), ("ly", ""),
             ("er", ""), ("ers", ""))


@lru_cache(maxsize=1)
def _ordinary_words() -> frozenset[str]:
    try:
        lines = _WORDS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:   # without the list every capitalised first word counts as a name, as before
        logger.warning("The list of ordinary words %s could not be read", _WORDS_FILE)
        return frozenset()
    return frozenset(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def is_ordinary_word(token: str) -> bool:
    """True for an ordinary English word ("Widowed", "Like", "Centre"), false for a name ("Iraq", "Trump", "Sudan"). The list holds
    the lowercase words that have no proper-noun entry of their own; a plural, past tense or British spelling counts as its base."""
    low = token.lower()
    words = _ordinary_words()
    candidates = {low}
    for suffix, replacement in _SUFFIXES:
        if low.endswith(suffix) and len(low) - len(suffix) >= 3:
            candidates.add(low[: -len(suffix)] + replacement)
    if low.endswith("re"):
        candidates.add(low[:-2] + "er")        # centre -> center
    if "our" in low:
        candidates.add(low.replace("our", "or"))   # labour -> labor
    if low.endswith("ise") or low.endswith("ised"):
        candidates.add(low.replace("is", "iz", 1) if "ise" in low else low)
    return any(c in words for c in candidates)


_YEAR = re.compile(r"(?:19|20)\d\d")
_OPENERS = set("how why what who whom whose when where which live inside exclusive explained watch video opinion analysis breaking update "
               "updates review podcast photos interview "
               # titles that come before a name ("Envoy Mikko ..."): the name matters, the title is written in many ways
               "envoy president minister governor mayor senator general chief prime secretary ambassador chairman premier king queen "
               "prince princess pope judge justice captain commander sheikh sir dr mr mrs ms lord lady spokesperson ex former".split())


def specifics(headline: str) -> list[str]:
    """The numbers and the names of an already normalised headline. A name is a capitalised word that is not in a headline written
    in Title Case (where every word is capitalised), not an abbreviation of up to three capital letters ("US", "PM", "NYT": too many
    spellings), not a word that only opens or labels a headline ("How", "Inside", "LIVE"), and not a function word. The first word
    counts, because it is the name in "Trump says ..." and the word "Iraq" in "Iraq wants diplomacy" is the very word that must not
    change; but it does not count when it is an ordinary English word ("Widowed", "Like"), which is capitalised only because it begins
    the headline. A year is not compared."""
    toks = _tokens(headline)
    words = [t for t in toks if len(t) > 3]
    title_case = len(words) >= 4 and sum(t[0].isupper() for t in words) / len(words) >= 0.6
    out = []
    for i, t in enumerate(toks):
        low = t.lower()
        if any(c.isdigit() for c in t):
            if not _YEAR.fullmatch(t):   # a year is often a target or a date that the text does not repeat
                out.append(_stem(low))
        elif (not title_case and t[0].isupper() and len(t) > 1 and low not in _STOP and low not in _OPENERS and not (t.isupper() and len(t) <= 3)
              and not (i == 0 and is_ordinary_word(t))):   # the first word is capitalised whatever it is
            out.append(_stem(low))
    return out


def missing_specifics(headline: str, text: str) -> list[str]:
    have = [_stem(t.lower()) for t in _tokens(text)]
    return sorted({w for w in specifics(headline) if not any(_same(w, h) for h in have)})


def _result(status: str, *, message: str, reason: str | None = None, best: dict | None = None, missing: list[str] | None = None,
            read: int = 0) -> dict[str, Any]:
    return {"status": status, "reason": reason, "message": message, "best": best, "missing": missing or [], "sentences_read": read,
            "rules": RULES, "limits": LIMITS}


def skipped(reason: str, message: str) -> dict[str, Any]:
    return _result("skipped", reason=reason, message=message)


def _lead(headline: str, text: str) -> list[str]:
    """The first sentences of the text, without lines that only repeat the headline or are too short to say anything."""
    out: list[str] = []
    short = len(headline.split()) + 3
    for sentence in split_sentences(text):
        words = sentence.split()
        if len(words) < 5 or (len(words) <= short and overlap(headline, sentence) >= REPEAT_OVERLAP):
            continue
        out.append(sentence)
        if len(out) >= LEAD_SENTENCES:
            break
    return out


def _windows(sentences: list[str]) -> list[str]:
    wins = list(sentences)
    for a, b in zip(sentences, sentences[1:]):
        pair = f"{a} {b}"
        if len(pair.split()) <= MAX_WINDOW_WORDS:
            wins.append(pair)
    return wins


def check(headline: str | None, text: str | None, nli) -> dict[str, Any]:
    """Run the check. Never raises: a problem becomes status 'unavailable' or 'skipped' with a reason."""
    headline = " ".join((headline or "").split())
    if not headline:
        return skipped("no_headline", "No headline was given, so the text could not be compared with one.")
    if len(headline.split()) < MIN_HEADLINE_WORDS:
        return skipped("headline_too_short", f"A headline of fewer than {MIN_HEADLINE_WORDS} words is too short to compare with the text.")
    if len((text or "").split()) < MIN_TEXT_WORDS:
        return skipped("text_too_short", f"A text of fewer than {MIN_TEXT_WORDS} words is too short to compare with its headline.")
    sentences = _lead(headline, text or "")
    if len(sentences) < 2:
        return skipped("text_too_short", "The text has too few sentences besides the headline to compare with it.")
    h = _normalise(headline)
    lead_text = _normalise(" ".join(sentences))
    full_text = _normalise(text or "")   # a number or name of the headline may come after the sentences that were read
    wins = _windows(sentences)
    norm_wins = [_normalise(w) for w in wins]
    overlaps = [overlap(h, w) for w in norm_wins]
    whole = overlap(h, lead_text)
    missing = missing_specifics(h, full_text)
    if not getattr(nli, "available", False):
        return _result("unavailable", reason="model_missing", read=len(sentences),
                       message="The inference model is not installed, so the text could not be compared with the headline.")
    try:
        scores = nli.predict([(w, headline) for w in wins])
    except Exception:
        logger.exception("Headline and text comparison failed")
        return _result("unavailable", reason="model_failed", read=len(sentences),
                       message="The inference model could not compare the text with the headline.")

    def row(i: int) -> dict[str, Any]:
        return {"text": wins[i], "overlap": round(overlaps[i], 2), "entailment": round(scores[i].get("entailment", 0.0), 2),
                "contradiction": round(scores[i].get("contradiction", 0.0), 2)}

    base = dict(read=len(sentences))
    entail = [i for i, p in enumerate(scores) if p.get("entailment", 0.0) >= SUPPORT_ENTAILMENT]
    if entail and not missing:
        i = max(entail, key=lambda k: scores[k]["entailment"])
        return _result("consistent", best=row(i), message="The first sentences of the text say what the headline says.", **base)
    question = headline.rstrip().endswith("?")   # a question claims nothing, so nothing in the text can contradict it
    contra = [i for i, p in enumerate(scores) if not question and overlaps[i] >= CONTRADICT_OVERLAP
              and p.get("contradiction", 0.0) >= CONTRADICT_PROBABILITY]
    if contra:
        i = max(contra, key=lambda k: scores[k]["contradiction"])
        return _result("contradicts", best=row(i), missing=missing, **base,
                       message="The text says something different from the headline. Read both before relying on either.")
    if whole < UNRELATED_OVERLAP:
        i = max(range(len(wins)), key=lambda k: overlaps[k])
        return _result("unrelated", best=row(i), missing=missing, **base,
                       message="The text does not seem to be about what the headline says. They may belong to different articles.")
    if whole >= SAME_SUBJECT_OVERLAP and missing:
        i = max(range(len(wins)), key=lambda k: overlaps[k])
        return _result("details_differ", best=row(i), missing=missing, **base,
                       message="The text is about the same subject, but " + ", ".join(missing[:4]) + " from the headline "
                               + ("does" if len(missing) == 1 else "do") + " not appear in it.")
    i = max(range(len(wins)), key=lambda k: (scores[k].get("entailment", 0.0), overlaps[k]))
    return _result("not_stated", best=row(i), missing=missing, **base,
                   message="The text is about the subject, but its first sentences do not clearly state what the headline says. "
                           "That alone does not mean either is wrong.")


# ---- how the result changes the verdict -------------------------------------------------------------------------

def same_publisher(match: dict[str, Any], outlet: str) -> dict[str, Any]:
    """A page served from a listed outlet's own website: the outlet wrote both the headline and the text, so nobody put a real
    headline over someone else's text, which is what this check looks for. A difference between them (an updated story under its
    first headline, a live page, a text the page reader read wrongly) is shown but does not change the verdict."""
    return {**match, "effect_note": f"This page is on the website of {outlet}, which wrote both the headline and the text, so a difference "
            "between them is shown here but does not change the result."}


MISMATCH = {"contradicts", "unrelated", "details_differ"}


def combine_text_match(result: dict[str, Any], match: dict[str, Any]) -> dict[str, Any]:
    """The result after the text was compared with its headline. It can only stop a 'Likely Real'; it never produces 'Likely Fake'.

      text and headline        Likely Real             Unverified        Likely Fake
      consistent / not stated  unchanged               unchanged         unchanged
      contradicts, unrelated,
      different details        Unverified (mismatch)   unchanged         unchanged
    """
    if match.get("status") in MISMATCH and result.get("verdict") == "Likely Real":
        return {**result, "verdict": "Unverified", "confidence": None, "reason": "headline_text_mismatch",
                "message": "The headline and the text under it do not match. " + match["message"] + " A match of the headline alone is not "
                           "enough to call this real."}
    return result
