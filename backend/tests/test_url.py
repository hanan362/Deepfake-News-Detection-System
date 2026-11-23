"""News URL analysis: the safe fetcher (SSRF), the article extractor, the source assessment, and the API.

No test here depends on the internet. A small local web server stands in for a news site, and only the very last step
(opening the TCP connection) is redirected to it, so the real address validation, DNS-answer check, redirect handling,
size and time limits all run for real."""
import http.server
import ipaddress
import socket
import threading
import time

import pytest

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.ml.text_detection.service import get_detector
from app.ml.url_analysis import fetch, source
from app.ml.url_analysis.extract import decode_html, extract
from app.models import AuditLog
from tests.conftest import API, ARTICLE

needs_model = pytest.mark.skipif(not get_detector().available, reason="text model not trained")

PUBLIC_IP = "93.184.216.34"


def page(paragraphs, *, title="City council approves budget", extra_head="", wrap="article"):
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{title} | Daily Test</title>{extra_head}</head>"
            f"<body><nav><p>Home News Sport Weather Contact this is only a menu entry with plenty of words in it</p></nav>"
            f"<{wrap}><h1>{title}</h1>{body}</{wrap}>"
            f"<footer><p>Copyright notice that is long enough to count as words if footers were not skipped properly</p></footer>"
            f"</body></html>")


ARTICLE_PARAS = [s.strip() + "." for s in ARTICLE.split(".") if s.strip()]
ARTICLE_HTML = page(ARTICLE_PARAS, extra_head=(
    '<meta name="author" content="Jane Doe"><meta property="article:published_time" content="2026-11-02T10:00:00Z">'
    '<script type="application/ld+json">{"@type":"NewsArticle","headline":"City council approves budget","datePublished":"2026-11-02"}</script>'))


class _Handler(http.server.BaseHTTPRequestHandler):
    log: list[tuple[str, str]] = []
    routes: dict = {}

    def log_message(self, *a):  # keep test output clean
        pass

    def do_GET(self):  # noqa: N802
        _Handler.log.append((self.headers.get("Host", ""), self.path))
        status, ctype, body, extra = self.routes.get(self.path.split("?")[0], (404, "text/plain", b"missing", {}))
        if callable(body):
            body = body()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        for k, v in extra.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def _slow():
    time.sleep(2.5)
    return b"<html><body><p>late</p></body></html>"


@pytest.fixture
def web(monkeypatch):
    """A fake news site on 127.0.0.1, reachable under any public-looking host name. Names containing 'internal' resolve
    to 10.0.0.5 and names containing 'rebind' resolve to a public AND a private address."""
    _Handler.log = []
    _Handler.routes = {
        "/article": (200, "text/html; charset=utf-8", ARTICLE_HTML.encode(), {}),
        "/plain": (200, "text/plain; charset=utf-8", ("\n\n".join(ARTICLE_PARAS)).encode(), {}),
        "/pdf": (200, "application/pdf", b"%PDF-1.4", {}),
        "/js-only": (200, "text/html", b"<html><body><div id='app'></div><script>render()</script></body></html>", {}),
        "/redir-ok": (302, "text/html", b"", {"Location": "/article"}),
        "/redir-internal": (302, "text/html", b"", {"Location": "http://internal.example/secret"}),
        "/redir-literal": (302, "text/html", b"", {"Location": "http://127.0.0.1/admin"}),
        "/redir-scheme": (302, "text/html", b"", {"Location": "file:///etc/passwd"}),
        "/loop": (302, "text/html", b"", {"Location": "/loop"}),
        "/big": (200, "text/html", lambda: b"<html><body>" + b"<p>word </p>" * 400_000 + b"</body></html>", {}),
        "/slow": (200, "text/html", _slow, {}),
        "/forbidden": (403, "text/html", b"no", {}),
    }
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    connected_to: list[str] = []

    def fake_getaddrinfo(host, p, *a, **k):
        ips = ["10.0.0.5"] if "internal" in host else [PUBLIC_IP, "127.0.0.1"] if "rebind" in host else [PUBLIC_IP]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, p)) for ip in ips]

    def fake_open(self):
        connected_to.append(self.pinned_ip)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # a raw socket: no DNS, so the patched resolver is not involved
        sock.settimeout(self.timeout)
        sock.connect(("127.0.0.1", port))
        return sock

    monkeypatch.setattr(fetch.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(fetch._Pinned, "_open_socket", fake_open)
    yield SimpleNamespace_(log=_Handler.log, connected_to=connected_to)
    server.shutdown()
    server.server_close()


class SimpleNamespace_:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ---------------------------------------------------------------- address validation (no network at all)

@pytest.mark.parametrize("url", [
    "http://127.0.0.1/", "http://2130706433/", "http://0x7f.1/", "http://017700000001/", "http://[::1]/", "http://localhost/",
    "http://169.254.169.254/latest/meta-data/", "http://10.0.0.1/", "http://user:pw@example.com/", "http://example.com:22/",
    "http://example.com:6379/", "http://printer.local/", "http://db.internal/", "http://example/", "http://-bad-.com/",
])
def test_dangerous_addresses_are_refused_before_any_connection(url):
    with pytest.raises(fetch.FetchError) as e:
        fetch.validate_url(url)
    assert e.value.code in {"URL_NOT_ALLOWED", "INVALID_URL"}


@pytest.mark.parametrize("url", ["", "   ", "ftp://example.com/x", "javascript:alert(1)", "file:///etc/passwd", "http://",
                                 "http://exa mple.com/", "http://example.com/\nHost: evil", "https://" + "a" * 1100 + ".com"])
def test_malformed_addresses_are_refused(url):
    with pytest.raises(fetch.FetchError) as e:
        fetch.validate_url(url)
    assert e.value.code in {"URL_NOT_ALLOWED", "INVALID_URL"}


def test_normal_addresses_are_normalised_and_idn_hosts_are_accepted():
    assert fetch.validate_url("HTTPS://Example.COM./a/b?x=1#frag")[:3] == ("https://example.com/a/b?x=1", "example.com", 443)
    assert fetch.validate_url("http://news.example:8080/x")[:3] == ("http://news.example:8080/x", "news.example", 8080)
    assert fetch.validate_url("http://bücher.de/")[1] == "xn--bcher-kva.de"


@pytest.mark.parametrize("ip,public", [
    ("8.8.8.8", True), ("2606:4700::1111", True), ("93.184.216.34", True),
    ("127.0.0.1", False), ("10.1.2.3", False), ("172.16.0.1", False), ("192.168.1.1", False), ("169.254.169.254", False),
    ("100.64.0.1", False), ("0.0.0.0", False), ("224.0.0.1", False), ("255.255.255.255", False),
    ("::1", False), ("fe80::1", False), ("fc00::1", False), ("::ffff:10.0.0.1", False), ("::ffff:127.0.0.1", False),
    ("2002:7f00:1::", False), ("64:ff9b::a00:1", False),
])
def test_only_public_addresses_pass(ip, public):
    assert fetch.is_public_ip(ipaddress.ip_address(ip)) is public


def test_a_name_with_any_private_answer_is_refused(monkeypatch):
    def answers(ips):
        return lambda host, p, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, p)) for ip in ips]
    monkeypatch.setattr(fetch.socket, "getaddrinfo", answers([PUBLIC_IP, "10.0.0.7"]))
    with pytest.raises(fetch.FetchError) as e:
        fetch.resolve_public("news.example", 80)
    assert e.value.code == "URL_NOT_ALLOWED"
    monkeypatch.setattr(fetch.socket, "getaddrinfo", answers([PUBLIC_IP]))
    assert fetch.resolve_public("news.example", 80) == PUBLIC_IP


def test_an_unresolvable_name_is_a_fetch_failure_not_a_crash(monkeypatch):
    def boom(*a, **k):
        raise socket.gaierror("no such host")
    monkeypatch.setattr(fetch.socket, "getaddrinfo", boom)
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://does-not-exist.example/")
    assert e.value.code == "URL_FETCH_FAILED" and e.value.status == 502


# ---------------------------------------------------------------- the fetcher against a local stand-in site

def test_a_page_is_read_over_the_address_that_was_checked(web):
    r = fetch.fetch("http://news.example/article")
    assert r.status == 200 and r.content_type == "text/html" and b"City council" in r.body and not r.truncated
    assert web.connected_to == [PUBLIC_IP]  # the connection used the validated address
    assert web.log[0][0] == "news.example"  # and the site was still asked for by name


def test_redirects_are_followed_and_recorded(web):
    r = fetch.fetch("http://news.example/redir-ok")
    assert r.final_url == "http://news.example/article" and r.redirects == ["http://news.example/redir-ok"]


@pytest.mark.parametrize("route", ["/redir-internal", "/redir-literal", "/redir-scheme"])
def test_a_redirect_into_the_internal_network_is_refused_and_never_followed(web, route):
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://news.example" + route)
    assert e.value.code in {"URL_NOT_ALLOWED", "INVALID_URL"}
    assert [p for _h, p in web.log] == [route]  # the internal target was never requested


def test_a_name_that_also_resolves_to_a_private_address_is_not_fetched(web):
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://rebind.example/article")
    assert e.value.code == "URL_NOT_ALLOWED" and web.log == []


def test_redirect_loops_stop(web):
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://news.example/loop")
    assert "too many times" in e.value.message and len(web.log) == fetch.MAX_REDIRECTS + 1


def test_only_html_and_plain_text_are_accepted(web):
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://news.example/pdf")
    assert e.value.code == "URL_NOT_A_PAGE" and e.value.status == 415
    assert fetch.fetch("http://news.example/plain").content_type == "text/plain"


def test_http_errors_say_what_to_do(web):
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://news.example/forbidden")
    assert e.value.code == "URL_FETCH_FAILED" and "refuses automated requests" in e.value.message and "paste" in e.value.message
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://news.example/nothing-here")
    assert "does not exist" in e.value.message


def test_a_huge_page_is_cut_at_the_size_limit_and_says_so(web):
    r = fetch.fetch("http://news.example/big")
    assert r.truncated and len(r.body) == fetch.MAX_BYTES


def test_a_slow_site_is_given_up_on(web, monkeypatch):
    monkeypatch.setattr(fetch, "SOCKET_TIMEOUT_SECONDS", 0.4)
    monkeypatch.setattr(fetch, "TOTAL_TIMEOUT_SECONDS", 1.0)
    started = time.monotonic()
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch("http://news.example/slow")
    assert e.value.status == 504 and time.monotonic() - started < 2.4


# ---------------------------------------------------------------- the article extractor

def test_the_article_body_is_kept_and_menus_footers_and_share_bars_are_dropped():
    html = page(ARTICLE_PARAS[:3] + ["Ok."], extra_head='<meta property="og:site_name" content="Daily Test">')
    html = html.replace("</article>", "<div class='share-bar'><p>Share this article with your friends on every network today</p></div></article>")
    e = extract(html)
    assert e.method == "article_element" and e.paragraphs == 3
    assert "menu entry" not in e.text and "Copyright notice" not in e.text and "Share this article" not in e.text and "Ok." not in e.text.split()
    assert e.headline == "City council approves budget" and e.site_name == "Daily Test" and e.language == "en"


def test_declared_metadata_is_read_from_meta_tags_and_json_ld():
    e = extract(ARTICLE_HTML)
    assert e.author == "Jane Doe" and e.published.startswith("2026-11-02") and e.declares_article


def test_without_an_article_element_longer_paragraphs_are_used():
    e = extract(page(ARTICLE_PARAS + ["Short one."], wrap="div"))
    assert e.method == "paragraphs" and e.word_count > 60 and "Short one" not in e.text


def test_a_page_built_by_javascript_yields_nothing_and_says_why():
    e = extract("<html><body><div id='app'></div><script>render()</script></body></html>")
    assert e.word_count == 0 and e.method == "none" and "JavaScript" in e.notes[0]


def test_the_html_tag_s_own_classes_do_not_hide_the_page():
    # real pages put classes such as "feature-main-menu-disabled" on <html>; that must not be read as a menu
    html = page(ARTICLE_PARAS).replace("<html lang='en'>", "<html lang='en' class='feature-main-menu-disabled'>")
    assert extract(html).word_count > 60


def test_inline_markup_does_not_add_stray_spaces():
    e = extract("<main><p>The council (<a href='#'>again</a>, as expected) voted <b>yes</b>, on Tuesday evening, to approve it.</p></main>")
    assert "(again, as expected) voted yes, on Tuesday" in e.text


def test_broken_html_does_not_crash():
    assert extract("<p>unclosed <div><span>text<p>more").word_count >= 0
    assert extract("").word_count == 0


def test_text_is_decoded_with_the_declared_charset_and_never_raises():
    assert decode_html("café".encode("latin-1"), "iso-8859-1") == "café"
    assert decode_html("<meta charset='windows-1256'>".encode() + "ٹ".encode("cp1256"), None).endswith("ٹ")
    assert decode_html(b"\xff\xfe broken", "no-such-charset")  # falls back instead of raising


# ---------------------------------------------------------------- source assessment

@pytest.mark.parametrize("host,expected", [
    ("www.reuters.com", "recognised_publisher"), ("news.bbc.co.uk", "recognised_publisher"), ("dawn.com", "recognised_publisher"),
    ("theonion.com", "declared_satire"),
    ("reuteres.com", "lookalike"), ("bbc.com.evil-site.net", "lookalike"), ("reuters-world-news.com", "lookalike"),
    ("nytimes.co", "lookalike"), ("dawn.net", "lookalike"),
    ("smalltownchronicle.org", "unknown"), ("dailytimes.com.pk", "unknown"), ("my-local-paper.example", "unknown"),
])
def test_source_outcomes(host, expected):
    url = f"https://{host}/a"
    assert source.assess(url, url, None)["assessment"] == expected


def test_a_subdomain_of_a_listed_site_matches_but_a_listed_name_inside_another_domain_does_not():
    assert source.match_entry("edition.cnn.com")["name"] == "CNN"
    assert source.match_entry("cnn.com.attacker.net") is None
    assert source.match_entry("notcnn.com") is None


def test_an_unfamiliar_site_is_never_called_fake_and_the_limits_are_listed():
    r = source.assess("https://smalltownchronicle.org/a", "https://smalltownchronicle.org/a", extract(ARTICLE_HTML))
    assert r["assessment"] == "unknown" and r["label"] == "Not enough information"
    assert "fake" not in r["label"].lower() and "unreliable" in r["summary"] and "score" not in r
    assert any("domain is" in x.lower() for x in r["not_checked"]) and r["caveat"]
    assert {s["effect"] for s in r["signals"]} <= {"supporting", "neutral", "caution"}


def test_signals_report_plain_facts_without_deciding():
    r = source.assess("https://bit.ly/abc", "http://news.example/a", extract("<html><link rel='canonical' href='https://other.example/x'><body></body></html>"))
    by_id = {s["id"]: s for s in r["signals"]}
    assert by_id["https"]["effect"] == "caution" and by_id["redirect"]["effect"] == "neutral" and by_id["canonical"]["effect"] == "caution"
    assert r["assessment"] == "unknown"  # signals never change the outcome


def test_the_directory_file_is_well_formed():
    d = source.directory()
    assert d["not_a_rating"] is True and len(d["entries"]) >= 40
    domains = [e["domain"] for e in d["entries"]]
    assert len(domains) == len(set(domains)) and {e["category"] for e in d["entries"]} <= {"wire_service", "broadcaster", "newspaper", "satire"}
    assert all(e["domain"] == e["domain"].lower() and "/" not in e["domain"] for e in d["entries"])


# ---------------------------------------------------------------- the API

def _post(client, user, url):
    return client.post(f"{API}/analysis/url", json={"url": url}, headers=user.headers)


@needs_model
def test_a_news_address_is_fetched_extracted_analysed_and_stored(client, alice, web):
    r = _post(client, alice, "http://news.example/article?utm=1")
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["analysis_type"] == "url" and a["source_url"] == "http://news.example/article?utm=1"
    d = a["details"]
    assert d["url"]["final"] == "http://news.example/article?utm=1" and d["url"]["http_status"] == 200 and not d["url"]["truncated"]
    assert d["url"]["extraction"]["method"] == "article_element" and d["url"]["extraction"]["author"] == "Jane Doe"
    assert d["source"]["assessment"] == "unknown" and "probabilities" in d and d["explanation"]["caution"]
    assert a["model"]["name"] == "text_baseline_en" and a["headline"] == "City council approves budget"
    assert "voted on Tuesday evening" in a["submitted_text"]  # the extracted text is shown, so the user can check it
    assert "whether the claims are true" in a["limitations"]
    assert client.get(f"{API}/analysis/{a['id']}", headers=alice.headers).json()["details"]["source"]["host"] == "news.example"


@needs_model
def test_url_analyses_appear_in_history_search_dashboard_and_pdf_and_can_be_deleted(client, alice, bob, web):
    a = _post(client, alice, "http://news.example/article").json()
    h = client.get(f"{API}/analysis?analysis_type=url", headers=alice.headers).json()
    assert h["total"] == 1 and h["items"][0]["id"] == a["id"] and h["items"][0]["details"] is None
    assert client.get(f"{API}/analysis?q=news.example", headers=alice.headers).json()["total"] == 1
    assert client.get(f"{API}/dashboard/stats", headers=alice.headers).json()["by_type"] == {"url": 1}
    pdf = client.get(f"{API}/analysis/{a['id']}/report.pdf", headers=alice.headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    import io
    from pypdf import PdfReader  # noqa: PLC0415  (only the report test needs it)
    text = " ".join(pg.extract_text() for pg in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Web address" in text and "news.example" in text and "Not enough information" in text
    assert client.get(f"{API}/analysis/{a['id']}", headers=bob.headers).status_code == 404
    assert client.delete(f"{API}/analysis/{a['id']}", headers=alice.headers).status_code == 204
    assert client.get(f"{API}/analysis/{a['id']}", headers=alice.headers).status_code == 404


@needs_model
def test_a_recognised_publisher_is_named_and_a_satire_site_gets_no_verdict(client, alice, web):
    r = _post(client, alice, "http://www.reuters.com/article").json()
    assert r["details"]["source"]["assessment"] == "recognised_publisher" and r["details"]["source"]["matched"]["name"] == "Reuters"
    s = _post(client, alice, "http://www.theonion.com/article").json()
    assert s["verdict"] == "Unverified" and s["details"]["reason"] == "declared_satire" and s["confidence"] is None
    assert "satire" in s["details"]["message"].lower()


def test_a_page_that_cannot_be_read_is_reported_not_guessed(client, alice, web):
    r = _post(client, alice, "http://news.example/js-only")
    assert r.status_code == 201
    a = r.json()
    assert a["verdict"] == "Unverified" and a["details"]["reason"] == "article_not_readable" and "probabilities" not in a["details"]
    assert "Paste the text" in a["details"]["message"] and a["details"]["source"]["assessment"] == "unknown"


def test_plain_text_pages_are_read_too(client, alice, web):
    a = _post(client, alice, "http://news.example/plain").json()
    assert a["details"]["url"]["extraction"]["method"] == "plain_text" and a["details"]["url"]["extraction"]["words"] > 60


@pytest.mark.parametrize("url,code,status", [
    ("http://127.0.0.1/admin", "URL_NOT_ALLOWED", 422), ("http://internal.example/x", "URL_NOT_ALLOWED", 422),
    ("ftp://news.example/x", "INVALID_URL", 422), ("http://news.example/pdf", "URL_NOT_A_PAGE", 415),
    ("http://news.example/redir-internal", "URL_NOT_ALLOWED", 422), ("http://news.example/forbidden", "URL_FETCH_FAILED", 502),
])
def test_unsafe_or_unreadable_addresses_fail_cleanly_and_store_nothing(client, alice, web, url, code, status):
    r = _post(client, alice, url)
    assert r.status_code == status and r.json()["error"]["code"] == code and r.json()["error"]["message"]
    assert client.get(f"{API}/analysis", headers=alice.headers).json()["total"] == 0


def test_the_endpoint_needs_login_and_a_valid_body(client, alice):
    assert client.post(f"{API}/analysis/url", json={"url": "http://news.example/a"}).status_code == 401
    assert client.post(f"{API}/analysis/url", json={}, headers=alice.headers).status_code == 422
    assert client.post(f"{API}/analysis/url", json={"url": "x" * 1001}, headers=alice.headers).status_code == 422


def test_it_can_be_switched_off(client, alice, web, monkeypatch):
    monkeypatch.setattr(get_settings(), "url_fetch_enabled", False)
    r = _post(client, alice, "http://news.example/article")
    assert r.status_code == 503 and r.json()["error"]["code"] == "URL_FETCH_DISABLED" and web.log == []
    models = {m["module"]: m for m in client.get(f"{API}/modules").json()["models"]}
    assert models["url"]["status"] == "unavailable"


def test_each_user_is_rate_limited_separately(client, alice, bob, web, monkeypatch):
    monkeypatch.setattr(get_settings(), "url_fetch_rate_limit_per_minute", 2)
    codes = [_post(client, alice, "http://news.example/js-only").status_code for _ in range(3)]
    assert codes == [201, 201, 429]
    assert _post(client, bob, "http://news.example/js-only").status_code == 201


def test_the_audit_trail_keeps_the_host_but_not_the_query_string(client, alice, web):
    _post(client, alice, "http://news.example/js-only?token=SECRET123")
    with SessionLocal() as db:
        rows = db.query(AuditLog).filter(AuditLog.action == "analysis.url").all()
    assert len(rows) == 1 and rows[0].detail["host"] == "news.example" and "SECRET123" not in str(rows[0].detail)


def test_the_registry_describes_the_url_module_honestly(client, admin):
    m = {x["module"]: x for x in client.get(f"{API}/models", headers=admin.headers).json()["models"]}["url"]
    assert m["status"] == "heuristic" and "never as fake" in m["description"]
    assert any("Not being listed says nothing" in x for x in m["limitations"])
