"""Pull the article text and its declared metadata out of an HTML page using only the standard library.

This is a heuristic reader, not a browser. It does not run JavaScript, so pages that build their text in the browser
(or hide it behind a subscription) come out empty or short, and the caller says so instead of guessing. The method:
metadata from <meta> tags and JSON-LD; text from the paragraphs inside <article>/<main> when they hold enough words,
otherwise from the longer paragraphs anywhere on the page; navigation, footers, forms, scripts and elements whose
class or id names them as sidebars, comments, share bars, adverts and the like are skipped.
"""
from __future__ import annotations

import codecs
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "nav", "header", "footer", "aside", "form",
             "button", "select", "option", "textarea", "head", "canvas", "dialog"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BOILERPLATE_TOKENS = {"comment", "comments", "sidebar", "share", "sharing", "social", "promo", "related", "newsletter",
                      "cookie", "cookies", "advert", "advertisement", "ads", "ad", "subscribe", "subscription", "menu",
                      "breadcrumb", "breadcrumbs", "widget", "popup", "modal", "banner", "paywall", "recommended"}
MIN_WORDS_IN_ARTICLE = 3
MIN_WORDS_OUTSIDE_ARTICLE = 8
# The class/id test is applied to container-like tags only. <html> and <body> carry class lists such as
# "vector-feature-main-menu-disabled", and skipping those would skip the whole page.
BOILERPLATE_TAGS = {"div", "section", "ul", "ol", "li", "span", "table", "figure", "a"}
ARTICLE_TYPES = {"newsarticle", "article", "reportagenewsarticle", "analysisnewsarticle", "opinionnewsarticle",
                 "reviewnewsarticle", "backgroundnewsarticle", "liveblogposting", "blogposting"}


@dataclass
class Extracted:
    title: str | None = None
    headline: str | None = None
    text: str = ""
    word_count: int = 0
    author: str | None = None
    published: str | None = None
    site_name: str | None = None
    language: str | None = None
    canonical_url: str | None = None
    declares_article: bool = False  # JSON-LD or og:type says this page is an article
    publisher: str | None = None
    method: str = "none"  # article_element | paragraphs | none
    paragraphs: int = 0
    notes: list[str] = field(default_factory=list)


def decode_html(body: bytes, header_charset: str | None) -> str:
    """Decode with the declared charset, then a <meta charset>, then UTF-8. Never raises."""
    candidates: list[str] = []
    if header_charset:
        candidates.append(header_charset)
    m = re.search(rb"<meta[^>]+charset\s*=\s*[\"']?\s*([A-Za-z0-9_.:-]+)", body[:4096], re.I)
    if m:
        candidates.append(m.group(1).decode("ascii", "ignore"))
    candidates.append("utf-8")
    for name in candidates:
        try:
            codecs.lookup(name)
            return body.decode(name, errors="replace")
        except (LookupError, ValueError):
            continue
    return body.decode("utf-8", errors="replace")


def _words(text: str) -> int:
    return len(text.split())


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _Reader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.h1: str | None = None
        self.lang: str | None = None
        self.canonical: str | None = None
        self.time_datetime: str | None = None
        self.jsonld: list[str] = []
        self.paragraphs: list[tuple[str, bool]] = []  # (text, inside article/main)
        self._stack: list[tuple[str, bool, bool]] = []  # tag, skips content, marks article scope
        self._skip_depth = 0
        self._article_depth = 0
        self._in_title = False
        self._in_h1 = False
        self._h1_parts: list[str] = []
        self._in_jsonld = False
        self._jsonld_parts: list[str] = []
        self._p_parts: list[str] | None = None

    # -- helpers
    @staticmethod
    def _boilerplate(attrs: dict[str, str]) -> bool:
        tokens = set(re.split(r"[\s_\-:]+", f"{attrs.get('class', '')} {attrs.get('id', '')}".lower()))
        return bool(tokens & BOILERPLATE_TOKENS)

    def handle_starttag(self, tag, attrs_list):
        attrs = {k: (v or "") for k, v in attrs_list}
        if tag == "html" and attrs.get("lang"):
            self.lang = attrs["lang"].strip()
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or attrs.get("itemprop") or "").lower()
            if key and attrs.get("content") and key not in self.meta:
                self.meta[key] = attrs["content"].strip()
            return
        if tag == "link":
            if "canonical" in attrs.get("rel", "").lower().split() and attrs.get("href"):
                self.canonical = attrs["href"].strip()
            return
        if tag == "script" and "ld+json" in attrs.get("type", "").lower():
            self._in_jsonld, self._jsonld_parts = True, []
        if tag == "time" and attrs.get("datetime") and not self.time_datetime and not self._skip_depth:
            self.time_datetime = attrs["datetime"].strip()
        if tag == "br" and self._p_parts is not None:
            self._p_parts.append(" ")
        if tag in VOID_TAGS:
            return
        skips = tag in SKIP_TAGS or (tag in BOILERPLATE_TAGS and self._boilerplate(attrs))
        marks_article = tag in ("article", "main") or attrs.get("itemprop", "").lower() == "articlebody" \
            or attrs.get("role", "").lower() == "main"
        self._stack.append((tag, skips, marks_article))
        if skips:
            self._skip_depth += 1
        if marks_article and not skips:
            self._article_depth += 1
        if tag == "title":
            self._in_title = True
        elif tag == "h1" and not self._skip_depth and self.h1 is None:
            self._in_h1, self._h1_parts = True, []
        elif tag == "p" and not self._skip_depth:
            self._p_parts = []

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if tag == "script" and self._in_jsonld:
            self.jsonld.append("".join(self._jsonld_parts))
            self._in_jsonld = False
        if tag == "title":
            self._in_title = False
        if tag == "h1" and self._in_h1:
            self._in_h1 = False
            self.h1 = _clean("".join(self._h1_parts)) or None
        if tag == "p" and self._p_parts is not None:
            text = _clean("".join(self._p_parts))
            self._p_parts = None
            if text:
                self.paragraphs.append((text, self._article_depth > 0))
        # close the matching open tag, tolerating the unclosed tags real pages are full of
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for _t, skips, marks in reversed(self._stack[i:]):
                    if skips:
                        self._skip_depth -= 1
                    if marks and not skips:
                        self._article_depth -= 1
                del self._stack[i:]
                if tag in ("p",) and self._p_parts is not None:
                    self._p_parts = None
                break

    def handle_data(self, data):
        if self._in_jsonld:
            self._jsonld_parts.append(data)
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._skip_depth:
            return
        if self._in_h1:
            self._h1_parts.append(data)
        if self._p_parts is not None:
            self._p_parts.append(data)


def _walk_jsonld(node, out: list[dict]) -> None:
    if isinstance(node, list):
        for x in node:
            _walk_jsonld(x, out)
    elif isinstance(node, dict):
        out.append(node)
        for v in node.values():
            if isinstance(v, (list, dict)):
                _walk_jsonld(v, out)


def _name(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _name(value.get("name"))
    if isinstance(value, list):
        names = [n for n in (_name(v) for v in value) if n]
        return ", ".join(names) or None
    return None


def extract(html: str) -> Extracted:
    reader = _Reader()
    try:
        reader.feed(html)
        reader.close()
    except Exception:  # the parser is lenient; if it still fails, work with what was read so far
        pass
    out = Extracted()
    meta = reader.meta
    ld_nodes: list[dict] = []
    for raw in reader.jsonld:
        try:
            _walk_jsonld(json.loads(raw), ld_nodes)
        except ValueError:
            continue
    article_ld = None
    for node in ld_nodes:
        types = node.get("@type")
        types = [types] if isinstance(types, str) else (types or [])
        if any(isinstance(t, str) and t.lower() in ARTICLE_TYPES for t in types):
            article_ld = node
            break
    title = _clean("".join(reader.title_parts)) or None
    out.title = title
    out.headline = ((article_ld or {}).get("headline") if isinstance((article_ld or {}).get("headline"), str) else None) \
        or meta.get("og:title") or meta.get("twitter:title") or reader.h1 or title
    out.headline = _clean(out.headline) if out.headline else None
    out.author = _name((article_ld or {}).get("author")) or meta.get("author") or meta.get("article:author")
    out.published = (article_ld or {}).get("datePublished") if isinstance((article_ld or {}).get("datePublished"), str) else None
    out.published = out.published or meta.get("article:published_time") or meta.get("datepublished") \
        or meta.get("date") or reader.time_datetime
    out.publisher = _name((article_ld or {}).get("publisher"))
    out.site_name = meta.get("og:site_name") or out.publisher
    out.language = reader.lang
    out.canonical_url = reader.canonical or meta.get("og:url")
    out.declares_article = article_ld is not None or meta.get("og:type", "").lower() == "article"

    in_article = [t for t, inside in reader.paragraphs if inside and _words(t) >= MIN_WORDS_IN_ARTICLE]
    anywhere = [t for t, _inside in reader.paragraphs if _words(t) >= MIN_WORDS_OUTSIDE_ARTICLE]
    if sum(_words(t) for t in in_article) >= 60:
        chosen, out.method = in_article, "article_element"
    elif anywhere:
        chosen, out.method = anywhere, "paragraphs"
    else:
        chosen = []
    # the same paragraph repeated (a "read more" teaser) is kept once
    seen: set[str] = set()
    unique = [t for t in chosen if not (t in seen or seen.add(t))]
    out.text = "\n\n".join(unique)
    out.word_count = _words(out.text)
    out.paragraphs = len(unique)
    if out.word_count == 0:
        out.notes.append("No article paragraphs were found. The page may build its text with JavaScript or hide it behind a login or subscription.")
    return out
