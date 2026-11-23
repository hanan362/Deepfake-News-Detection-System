"""Search recent news headlines.

The provider reads the public RSS feed of Google News search. It is NOT an official, documented API: Google can change or
stop it, and its terms of use apply. The rest of the application only sees the small `NewsSearch` interface, so another
source can replace it without other changes. Only the headline typed by the user is sent. Nothing else leaves the server.
"""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from threading import Lock
from typing import Protocol
from urllib.parse import urlsplit

import httpx

FEED_URL = "https://news.google.com/rss/search"
MAX_BYTES = 1_500_000
USER_AGENT = "DeepfakeNewsDetectionSystem/1.0 (student research project; headline lookup)"
CACHE_SECONDS = 600
CACHE_SIZE = 256
RETRY_WAIT_SECONDS = 1.5      # one short pause before the single retry after an HTTP 429
RETRY_AFTER_CAP_SECONDS = 3.0  # a Retry-After header is honoured only up to this long (a request must not hang)
COOLDOWN_SECONDS = 60.0       # after a second 429 the search is not called again for this long
COOLDOWN_CAP_SECONDS = 300.0  # a longer Retry-After than this is still capped, so a bad header cannot disable it for hours


@dataclass(frozen=True)
class NewsHit:
    title: str            # the headline, without the outlet name
    outlet: str | None    # the outlet's own name as the feed gives it
    site_url: str | None  # the outlet's home page, used to match the directory
    link: str | None      # the address the feed gives for the story
    published: str | None


class SearchUnavailable(Exception):
    """The search could not be made (network error, blocked, malformed answer). The message is for the user."""


class NewsSearch(Protocol):
    name: str

    def search(self, query: str, limit: int = 12) -> list[NewsHit]: ...


def _strip_outlet(title: str, outlet: str | None) -> str:
    title = " ".join(title.split())
    if outlet and title.endswith(" - " + outlet):
        return title[: -len(outlet) - 3].rstrip()
    return re.sub(r"\s+-\s+[^-]{2,40}$", "", title)


def parse_feed(body: bytes, limit: int = 12) -> list[NewsHit]:
    """Read the items of an RSS feed. Documents that declare entities or a DOCTYPE are refused (expansion attacks)."""
    head = body[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in body[:20000].lower():
        raise SearchUnavailable("The news search returned a document that was not accepted.")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise SearchUnavailable("The news search returned something that is not a news feed.") from exc
    hits: list[NewsHit] = []
    for item in root.iter("item"):
        source = item.find("source")
        outlet = (source.text or "").strip() if source is not None and source.text else None
        site = source.get("url") if source is not None else None
        title = _strip_outlet(item.findtext("title") or "", outlet)
        if not title:
            continue
        hits.append(NewsHit(title=title, outlet=outlet, site_url=site, link=item.findtext("link"), published=item.findtext("pubDate")))
        if len(hits) >= limit:
            break
    return hits


class GoogleNewsSearch:
    name = "Google News RSS (unofficial)"

    def __init__(self, timeout: float = 8.0, client: httpx.Client | None = None, sleep=time.sleep):
        self.timeout = timeout
        self._client = client
        self._sleep = sleep
        self._cache: dict[str, tuple[float, list[NewsHit]]] = {}
        self._lock = Lock()
        self._paused_until = 0.0

    def _get(self, params: dict) -> httpx.Response:
        headers = {"User-Agent": USER_AGENT}
        try:
            if self._client is not None:
                return self._client.get(FEED_URL, params=params, headers=headers, timeout=self.timeout)
            return httpx.get(FEED_URL, params=params, headers=headers, timeout=self.timeout, follow_redirects=False)
        except httpx.HTTPError as exc:
            raise SearchUnavailable("The news search could not be reached.") from exc

    @staticmethod
    def _retry_after(resp: httpx.Response) -> float | None:
        raw = resp.headers.get("Retry-After", "").strip()
        return float(raw) if raw.isdigit() else None

    def search(self, query: str, limit: int = 12) -> list[NewsHit]:
        key = query.strip().lower()
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(key)
            if cached and now - cached[0] < CACHE_SECONDS:
                return cached[1][:limit]
            paused = self._paused_until - now
        if paused > 0:
            raise SearchUnavailable(f"The news search asked this server to slow down. The headline check is paused for about {int(paused) + 1} more seconds.")
        params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
        resp = self._get(params)
        if resp.status_code == 429:
            # One short retry, then stop asking for a while so that a blocked server does not keep sending requests.
            wait = min(self._retry_after(resp) or RETRY_WAIT_SECONDS, RETRY_AFTER_CAP_SECONDS)
            self._sleep(wait)
            resp = self._get(params)
            if resp.status_code == 429:
                pause = min(self._retry_after(resp) or COOLDOWN_SECONDS, COOLDOWN_CAP_SECONDS)
                with self._lock:
                    self._paused_until = time.monotonic() + pause
                raise SearchUnavailable(f"The news search is limiting requests right now. The headline check is paused for about {int(pause)} seconds; the other results are not affected.")
        if resp.status_code != 200:
            raise SearchUnavailable(f"The news search answered with an error (HTTP {resp.status_code}).")
        if len(resp.content) > MAX_BYTES:
            raise SearchUnavailable("The news search answer was larger than expected and was not read.")
        hits = parse_feed(resp.content, limit)
        with self._lock:
            if len(self._cache) >= CACHE_SIZE:
                self._cache.pop(next(iter(self._cache)))
            self._cache[key] = (now, hits)
        return hits


def host_of(url: str | None) -> str:
    return (urlsplit(url or "").hostname or "").lower()


_provider: GoogleNewsSearch | None = None


def get_news_search() -> NewsSearch:
    """The provider the application uses. Tests replace this function."""
    global _provider
    if _provider is None:
        from app.core.config import get_settings

        _provider = GoogleNewsSearch(timeout=getattr(get_settings(), "corroboration_timeout_seconds", 8.0))
    return _provider
