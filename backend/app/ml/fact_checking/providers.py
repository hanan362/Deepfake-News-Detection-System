"""Where evidence comes from. Each provider reports its own status, so a failure or a missing API key is shown to the
user instead of silently turning into "no evidence".

* Wikipedia: keyless. An encyclopedia, so it shows what is generally documented, not what happened in this week's news.
* Google Fact Check Tools: needs GOOGLE_FACT_CHECK_API_KEY. Returns published fact-check ratings with their publisher.

The addresses are fixed in code, never taken from user input, so these requests cannot be steered anywhere else."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

USER_AGENT = "DeepfakeNewsDetectionSystem/0.1 (student research project; evidence lookup)"
TIMEOUT_SECONDS = 8
# Wikipedia (and shared networks) sometimes answer 429 or 503 for a moment. A short, bounded retry hides that without
# hammering the service: at most MAX_ATTEMPTS requests, waiting the server's Retry-After (capped) or 1 s, 2 s.
RETRY_STATUS = (429, 503)
MAX_ATTEMPTS = 3
MAX_WAIT_SECONDS = 4.0
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
FACT_CHECK_API = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
_STOP = set("the a an of in on at to for and or but is are was were be been being by with from as that this these those it its he she they his her their has have had will would can could not no".split())


@dataclass
class Evidence:
    provider: str
    kind: str  # encyclopedia | fact_check
    title: str
    url: str
    text: str
    published: str | None = None
    rating: str | None = None  # fact_check only: the publisher's own rating, as published
    publisher: str | None = None


@dataclass
class ProviderResult:
    provider: str
    status: str  # ok | not_configured | error | no_results
    message: str = ""
    evidence: list[Evidence] = field(default_factory=list)


class Provider(Protocol):
    name: str

    def search(self, claim: str) -> ProviderResult: ...


def content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z0-9']+", text.lower()) if w not in _STOP and len(w) > 1]


_LEADING_DETERMINER = {"the", "a", "an"}
_NAME_CONNECTORS = {"of", "the", "de", "da", "di", "del", "la", "le", "al", "van", "von", "bin"}
SUBJECT_PAGES = 2   # pages taken from the second search, made with the claim's subject alone
CLAIM_PAGES = 3     # pages taken from the search made with the claim's own words


def subject_phrase(claim: str) -> str | None:
    """The name the claim starts with: "The Eiffel Tower is located in Rome" -> "Eiffel Tower", "Apollo 11 landed ..." -> "Apollo 11".

    Why: a search made with every word of a claim is pulled toward pages that share its wrong details ("Rome, Italy"), so the page
    about the subject itself can be missing and the verdict then rests on an unrelated sentence. A second, short search for the
    subject alone finds that page. This is a spelling heuristic (capitalised words at the start), not language understanding; a
    claim that does not start with a name gets no second search."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019-]*|[,;:.]", claim)
    i = 1 if tokens and tokens[0].lower() in _LEADING_DETERMINER else 0
    phrase: list[str] = []
    while i < len(tokens):
        t = tokens[i]
        if t in ",;:.":
            break
        if t[0].isupper() or t[0].isdigit():
            phrase.append(t)
        elif t.lower() in _NAME_CONNECTORS and phrase and i + 1 < len(tokens) and tokens[i + 1][0].isupper():
            phrase.append(t)
        else:
            break
        i += 1
    return " ".join(phrase) if any(w[0].isupper() for w in phrase) else None  # a number alone is not a name


def merge_evidence(subject_pages: list["Evidence"], claim_pages: list["Evidence"]) -> list["Evidence"]:
    """Pages about the subject first, then the pages the claim's own words found; a page that appears twice is kept once."""
    seen: set[str] = set()
    out: list[Evidence] = []
    for ev in [*subject_pages[:SUBJECT_PAGES], *claim_pages[:CLAIM_PAGES]]:
        key = ev.title.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(ev)
    return out


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _retry_wait(exc: urllib.error.HTTPError, attempt: int) -> float:
    """Seconds to wait before the next try: the server's Retry-After when it is a plain number, else 1 s, 2 s ... Always capped."""
    header = exc.headers.get("Retry-After") if exc.headers else None
    try:
        wait = float(header) if header is not None else float(2 ** (attempt - 1))
    except (TypeError, ValueError):  # a date-form Retry-After is not used; fall back to the plain back-off
        wait = float(2 ** (attempt - 1))
    return max(0.0, min(wait, MAX_WAIT_SECONDS))


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310  (fixed https addresses)
                return json.loads(resp.read(2_000_000).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRY_STATUS or attempt == MAX_ATTEMPTS:
                raise  # the caller turns this into a message the user sees
            _sleep(_retry_wait(exc, attempt))
    raise AssertionError("unreachable")  # pragma: no cover


class WikipediaProvider:
    name = "wikipedia"

    def __init__(self, limit: int = CLAIM_PAGES):
        self.limit = limit

    @staticmethod
    def _query(words: str, limit: int) -> str:
        params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": words, "gsrlimit": limit,
                  "prop": "extracts|info", "inprop": "url", "exintro": 1, "explaintext": 1, "exsentences": 10, "redirects": 1}
        return f"{WIKIPEDIA_API}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def _pages(data: dict) -> list[Evidence]:
        pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
        return [Evidence("wikipedia", "encyclopedia", p.get("title", ""), p.get("fullurl", ""), (p.get("extract") or "").strip())
                for p in pages if (p.get("extract") or "").strip()]

    def search(self, claim: str) -> ProviderResult:
        query = " ".join(content_words(claim)[:14])
        if not query:
            return ProviderResult(self.name, "no_results", "The claim has no searchable words.")
        try:
            claim_pages = self._pages(_get_json(self._query(query, self.limit)))
        except urllib.error.HTTPError as exc:
            msg = "Wikipedia is limiting requests right now. Try again in a minute." if exc.code == 429 else f"Wikipedia answered with an error ({exc.code})."
            return ProviderResult(self.name, "error", msg)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return ProviderResult(self.name, "error", "Wikipedia could not be reached.")
        subject_pages: list[Evidence] = []
        subject = subject_phrase(claim)
        if subject and subject.lower() != query.lower():
            try:  # the extra search only adds pages; if it fails, the first search's pages are still used
                subject_pages = self._pages(_get_json(self._query(subject, SUBJECT_PAGES)))
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                subject_pages = []
        items = merge_evidence(subject_pages, claim_pages)
        if not items:
            return ProviderResult(self.name, "no_results", "Wikipedia has no page that matches this claim.")
        return ProviderResult(self.name, "ok", f"{len(items)} pages", items)


class GoogleFactCheckProvider:
    name = "google_fact_check"

    def __init__(self, api_key: str | None, limit: int = 5):
        self.api_key, self.limit = api_key, limit

    def search(self, claim: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(self.name, "not_configured", "No API key is set (GOOGLE_FACT_CHECK_API_KEY), so published fact-checks were not searched.")
        params = {"query": claim[:200], "pageSize": self.limit, "languageCode": "en", "key": self.api_key}
        try:
            data = _get_json(f"{FACT_CHECK_API}?{urllib.parse.urlencode(params)}")
        except urllib.error.HTTPError as exc:
            return ProviderResult(self.name, "error", f"The fact-check service answered with an error ({exc.code}). Check the API key.")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return ProviderResult(self.name, "error", "The fact-check service could not be reached.")
        items: list[Evidence] = []
        for c in data.get("claims", []):
            for r in c.get("claimReview", [])[:1]:
                items.append(Evidence(self.name, "fact_check", r.get("title") or c.get("text", ""), r.get("url", ""),
                                      c.get("text", ""), (r.get("reviewDate") or None), r.get("textualRating"),
                                      (r.get("publisher") or {}).get("name")))
        if not items:
            return ProviderResult(self.name, "no_results", "No published fact-check matches this claim.")
        return ProviderResult(self.name, "ok", f"{len(items)} fact-checks", items)
