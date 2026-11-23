"""Pick the sentences of a text that look like checkable factual claims.

A heuristic, not a model: a sentence is a candidate when it is a statement of moderate length that contains a number or
a name (a capitalised word that is not the first word), and it is not a question, an opinion marker or a quotation
fragment. The result is a list the user can read, so a bad pick is visible and can be replaced by pasting the claim."""
from __future__ import annotations

import re

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(\d])")
_OPINION = re.compile(r"\b(i think|i believe|in my opinion|we believe|should|must|might|may be|could be|allegedly|reportedly)\b", re.I)
_NUMBER = re.compile(r"\d")
MIN_WORDS, MAX_WORDS = 6, 45


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    return [s.strip() for s in _SENT.split(text) if s.strip()]


def _score(sentence: str) -> int:
    words = sentence.split()
    names = sum(1 for w in words[1:] if w[:1].isupper() and w.rstrip(".,;:").lower() not in {"the", "a", "an", "he", "she", "it", "they"})
    score = names + 2 * bool(_NUMBER.search(sentence))
    if re.search(r"\b(said|announced|declared|confirmed|reported|found|killed|died|won|lost|elected|approved|signed|arrested|born)\b", sentence, re.I):
        score += 1
    return score


def extract_claims(text: str, limit: int = 5) -> list[str]:
    """At most `limit` claims, in the order they appear in the text."""
    candidates: list[tuple[int, int, str]] = []
    for i, s in enumerate(split_sentences(text)):
        n = len(s.split())
        if not (MIN_WORDS <= n <= MAX_WORDS) or s.endswith("?") or _OPINION.search(s):
            continue
        sc = _score(s)
        if sc >= 2:
            candidates.append((sc, i, s))
    best = sorted(candidates, key=lambda c: (-c[0], c[1]))[:limit]
    return [s for _sc, _i, s in sorted(best, key=lambda c: c[1])]
