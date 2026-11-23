"""Starts the real API server for the browser tests, with ONE difference: a small stand-in news site is reachable under
fictional host names (anything ending in .example, plus www.reuters.com and www.theonion.com), so the whole "read a news
address" flow can be exercised without the internet. A second stand-in is for video: the browser tests have no video of a real
person, so a frame with a magenta square in its corner is reported as containing a face (the real classifier then scores
that frame); every other frame goes through the real face detector. Only the last step, opening the TCP connection, is redirected. The
address validation, the public-address check on the DNS answer, redirect handling and all limits are the production code.
This file is a test harness; nothing in the application knows about it."""
import http.server
import os
import socket
import sys
import threading

BACKEND = os.environ["E2E_BACKEND_DIR"]
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

from app.ml.url_analysis import fetch  # noqa: E402

PARAS = [
    "The harbour authority announced on Monday that the new ferry terminal will open to passengers in March after two years of construction and several delays caused by storms.",
    "Officials said the terminal will handle about four thousand passengers a day and includes a covered walkway to the nearby bus station, a small market hall and an expanded car park for residents.",
    "A spokesperson for the authority told reporters that the project stayed within its approved budget because the contractor absorbed the cost of the repairs needed after the winter storms damaged the pier.",
    "Local business owners welcomed the announcement, although some said that the new parking charges could discourage short visits, and they asked the council to review the fees after the first six months of operation.",
    "The authority will publish monthly passenger numbers on its website, and an independent review of the project's finances is expected to be completed before the end of the year.",
]
ARTICLE = ("<!doctype html><html lang='en'><head><meta charset='utf-8'><title>New ferry terminal to open in March | Harbour Gazette</title>"
           "<meta name='author' content='A. Reporter'><meta property='article:published_time' content='2026-11-03T08:30:00Z'>"
           "<meta property='og:site_name' content='Harbour Gazette'></head><body><nav><p>Home News Sport Weather Contact us this is only a menu with plenty of words in it</p></nav>"
           "<article><h1>New ferry terminal to open in March</h1>" + "".join(f"<p>{p}</p>" for p in PARAS) +
           "</article><footer><p>Copyright notice that is long enough to count as words if the footer were not skipped</p></footer></body></html>")
ROUTES = {
    "/ferry-terminal": ("text/html; charset=utf-8", ARTICLE.encode()),
    "/js-only": ("text/html", b"<html><body><div id='app'></div><script>render()</script></body></html>"),
    "/report.pdf": ("application/pdf", b"%PDF-1.4"),
}
PUBLIC_IP = "93.184.216.34"


WIKI = "en.wikipedia.org"
WIKI_PAGES = {  # canned answer of the Wikipedia search API, so the evidence flow runs without the internet
    "pages": {"1": {"index": 1, "title": "Jackie (2016 film)", "fullurl": "https://en.wikipedia.org/wiki/Jackie_(2016_film)",
                    "extract": "Jackie is a 2016 biographical drama film directed by Pablo Larra\u00edn and written by Noah Oppenheim. It stars Natalie Portman as Jacqueline Kennedy."}}}


def standin(host: str) -> bool:
    return host.endswith(".example") or host in ("www.reuters.com", "www.theonion.com")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):  # noqa: N802
        ctype, body = ROUTES.get(self.path.split("?")[0], ("text/plain", b"missing"))
        self.send_response(200 if self.path.split("?")[0] in ROUTES else 404)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
STANDIN_PORT = server.server_address[1]

real_getaddrinfo = socket.getaddrinfo
real_open = fetch._Pinned._open_socket


def fake_getaddrinfo(host, port, *args, **kwargs):
    if isinstance(host, str) and standin(host):
        ip = "10.0.0.5" if "internal" in host else PUBLIC_IP
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
    return real_getaddrinfo(host, port, *args, **kwargs)


def fake_open(self):
    if standin(self.host):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect(("127.0.0.1", STANDIN_PORT))
        return s
    return real_open(self)


from app.ml.fact_checking import providers as _providers  # noqa: E402

_real_get_json = _providers._get_json


def _fake_get_json(url):
    if url.startswith(_providers.WIKIPEDIA_API):
        return {"query": WIKI_PAGES}
    return _real_get_json(url)


_providers._get_json = _fake_get_json

# Stand-in for the news search (Google News RSS): canned headlines for the headlines the browser tests use, nothing for any other.
from app.ml.corroboration import news_search as _news  # noqa: E402

_NEWS = {
    "new ferry terminal to open in march": [
        _news.NewsHit("New ferry terminal set to open in March after storm delays", "Reuters", "https://www.reuters.com", "https://news.example/reuters-ferry", "Mon, 02 Nov 2026 09:00:00 GMT")],
    "harbour authority confirms new ferry terminal will open in march": [
        _news.NewsHit("Harbour authority says new ferry terminal will not open in March", "BBC", "https://www.bbc.com", "https://news.example/bbc-ferry", "Mon, 02 Nov 2026 10:00:00 GMT")],
}


class _StandInNews:
    name = "stand-in news search (browser tests)"

    def search(self, query, limit=12):
        return list(_NEWS.get(query.strip().lower(), []))


_news._provider = _StandInNews()
socket.getaddrinfo = fake_getaddrinfo
fetch._Pinned._open_socket = fake_open

from app.ml.video_detection import faces as _faces  # noqa: E402

_real_largest_face = _faces.largest_face


def _marker_face(frame):
    import numpy as np

    corner = frame[2:36, 2:36].reshape(-1, 3).mean(axis=0)  # BGR; a lossy codec shifts the colour a little
    if np.abs(corner - np.array([255, 0, 255])).max() < 70:
        h, w = frame.shape[:2]
        x0, y0, x1, y1 = int(w * 0.15), int(h * 0.1), int(w * 0.85), int(h * 0.9)
        return _faces.Face((x0, y0, x1 - x0, y1 - y0), frame[y0:y1, x0:x1][:, :, ::-1].copy(), 0.7, 0.99)
    return _real_largest_face(frame)


_faces.largest_face = _marker_face

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("E2E_API_PORT", "8765")), log_level="warning")
