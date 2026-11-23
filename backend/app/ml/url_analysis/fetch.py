"""Fetch one web page on behalf of a user without letting them reach the server's own network (SSRF).

The server downloads whatever address a signed-in user types in, so the address is untrusted input. What this module
enforces, and what the tests check:

* only http and https, only ports 80, 443, 8080 and 8443, no user name or password in the address;
* the host must be a real domain name (an IP address in any notation, including 2130706433 or 0x7f.1, is refused);
* the name is resolved ONCE, every returned address must be public, and the connection goes to that address. A second,
  different DNS answer therefore cannot redirect the request to an internal host (DNS rebinding);
* each redirect is checked again from the start, at most five of them;
* a total time limit, a size limit (the rest of a big page is dropped and the result says so), no compression
  (so a small download cannot expand into a huge one), and only HTML or plain text is accepted.

It does not run JavaScript, does not log in and does not crawl: one page, because the user asked for that page.
"""
from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

ALLOWED_PORTS = {80, 443, 8080, 8443}
MAX_URL_LENGTH = 1000
MAX_REDIRECTS = 5
MAX_BYTES = 2 * 1024 * 1024
TOTAL_TIMEOUT_SECONDS = 15.0
SOCKET_TIMEOUT_SECONDS = 6.0
ACCEPTED_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
USER_AGENT = "DeepfakeNewsDetectionSystem/0.1 (student research project; fetches only pages its user submits)"
_DOMAIN_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
_TLD = re.compile(r"^([a-z]{2,63}|xn--[a-z0-9-]{1,59})$")
_BLOCKED_SUFFIXES = (".local", ".localhost", ".internal", ".intranet", ".lan", ".home", ".corp", ".localdomain")


class FetchError(Exception):
    """A page could not be fetched. `code` is stable and shown to the API client; `message` explains what to do."""

    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass
class FetchResult:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    charset: str | None
    body: bytes
    truncated: bool
    redirects: list[str] = field(default_factory=list)
    elapsed_ms: int = 0


def is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True only for addresses that belong on the public internet. Embedded IPv4 addresses are unwrapped first, so
    ::ffff:127.0.0.1, 6to4, Teredo and NAT64 forms cannot be used to hide a private address."""
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return is_public_ip(ip.ipv4_mapped)
        if ip.sixtofour is not None:
            return is_public_ip(ip.sixtofour) and ip.is_global
        if ip.teredo is not None:
            return is_public_ip(ip.teredo[1]) and ip.is_global
        if ip in ipaddress.ip_network("64:ff9b::/96"):
            return is_public_ip(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
    return bool(ip.is_global) and not ip.is_multicast


def validate_url(url: str) -> tuple[str, str, int, str]:
    """Check the address itself. Returns (normalised url, host, port, path with query). Does not touch the network."""
    url = (url or "").strip()
    if not url or len(url) > MAX_URL_LENGTH:
        raise FetchError("INVALID_URL", f"Enter a web address of at most {MAX_URL_LENGTH} characters.")
    if any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise FetchError("INVALID_URL", "The web address contains spaces or control characters.")
    parts = urlsplit(url)
    if parts.scheme.lower() not in ("http", "https"):
        raise FetchError("INVALID_URL", "Only http:// and https:// addresses can be read.")
    if parts.username is not None or parts.password is not None:
        raise FetchError("URL_NOT_ALLOWED", "Addresses with a user name or password are not accepted.")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise FetchError("INVALID_URL", "The web address has no host name.")
    try:
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError:
        raise FetchError("INVALID_URL", "The port in the web address is not valid.")
    if port not in ALLOWED_PORTS:
        raise FetchError("URL_NOT_ALLOWED", "Only the standard web ports (80, 443, 8080, 8443) are accepted.")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise FetchError("INVALID_URL", "The host name is not valid.")
    labels = ascii_host.split(".")
    # A real news site has a name with a letter-based last label. This also rejects every notation of an IP address.
    if len(labels) < 2 or not all(_DOMAIN_LABEL.match(x) for x in labels) or not _TLD.match(labels[-1]):
        raise FetchError("URL_NOT_ALLOWED", "Use the website's domain name, not an IP address or an internal host name.")
    if ascii_host == "localhost" or ascii_host.endswith(_BLOCKED_SUFFIXES):
        raise FetchError("URL_NOT_ALLOWED", "Internal host names are not accepted.")
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    scheme = parts.scheme.lower()
    default = 443 if scheme == "https" else 80
    netloc = ascii_host if port == default else f"{ascii_host}:{port}"
    return f"{scheme}://{netloc}{path}", ascii_host, port, path


def resolve_public(host: str, port: int) -> str:
    """Resolve once and return one public address. If ANY answer is not public the whole name is refused."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise FetchError("URL_FETCH_FAILED", "The website's address could not be found. Check the spelling.", 502)
    except OSError:
        raise FetchError("URL_FETCH_FAILED", "The website's address could not be looked up right now.", 502)
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for info in infos:
        try:
            addresses.append(ipaddress.ip_address(info[4][0].split("%")[0]))
        except ValueError:
            continue
    if not addresses:
        raise FetchError("URL_FETCH_FAILED", "The website's address could not be found. Check the spelling.", 502)
    if not all(is_public_ip(a) for a in addresses):
        raise FetchError("URL_NOT_ALLOWED", "This address points to a private or internal network, so it is not fetched.")
    return str(sorted(addresses, key=lambda a: a.version)[0])


class _Pinned:
    """Mixin: connect to an address that was already checked, never to a fresh DNS answer."""

    pinned_ip: str

    def _open_socket(self):
        return socket.create_connection((self.pinned_ip, self.port), self.timeout)


class _HTTPConnection(_Pinned, http.client.HTTPConnection):
    def connect(self):
        self.sock = self._open_socket()


class _HTTPSConnection(_Pinned, http.client.HTTPSConnection):
    def connect(self):
        sock = self._open_socket()
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _charset(content_type: str) -> str | None:
    m = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9_.:-]+)", content_type, re.I)
    return m.group(1).lower() if m else None


def fetch(url: str) -> FetchResult:
    started = time.monotonic()
    deadline = started + TOTAL_TIMEOUT_SECONDS
    current, host, port, path = validate_url(url)
    redirects: list[str] = []
    context = ssl.create_default_context()
    for _hop in range(MAX_REDIRECTS + 1):
        ip = resolve_public(host, port)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FetchError("URL_FETCH_FAILED", "The website took too long to answer.", 504)
        timeout = min(SOCKET_TIMEOUT_SECONDS, remaining)
        https = current.startswith("https://")
        conn = (_HTTPSConnection(host, port, timeout=timeout, context=context) if https
                else _HTTPConnection(host, port, timeout=timeout))
        conn.pinned_ip = ip
        try:
            conn.request("GET", path, headers={
                "User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,text/plain;q=0.5",
                "Accept-Language": "en,ur;q=0.8", "Accept-Encoding": "identity", "Connection": "close"})
            resp = conn.getresponse()
            status = resp.status
            if status in (301, 302, 303, 307, 308):
                location = resp.getheader("Location")
                if not location:
                    raise FetchError("URL_FETCH_FAILED", "The website redirected without saying where.", 502)
                if len(redirects) >= MAX_REDIRECTS:
                    raise FetchError("URL_FETCH_FAILED", "The website redirected too many times.", 502)
                redirects.append(current)
                current, host, port, path = validate_url(urljoin(current, location.strip()))
                continue
            if status >= 400:
                hint = {401: " It needs a login.", 403: " It refuses automated requests.", 404: " The page does not exist.",
                        429: " It is limiting requests; try again later."}.get(status, "")
                raise FetchError("URL_FETCH_FAILED", f"The website answered with an error ({status}).{hint} "
                                 "You can paste the article text instead.", 502)
            ctype_header = resp.getheader("Content-Type") or ""
            ctype = ctype_header.split(";")[0].strip().lower()
            if ctype not in ACCEPTED_TYPES:
                raise FetchError("URL_NOT_A_PAGE", f"This address is not a web page ({ctype or 'unknown type'}). "
                                 "Only HTML pages and plain text can be read.", 415)
            body = bytearray()
            truncated = False
            while True:
                if time.monotonic() > deadline:
                    raise FetchError("URL_FETCH_FAILED", "The website took too long to send the page.", 504)
                chunk = resp.read(16 * 1024)
                if not chunk:
                    break
                body += chunk
                if len(body) > MAX_BYTES:
                    del body[MAX_BYTES:]
                    truncated = True
                    break
            return FetchResult(requested_url=url.strip(), final_url=current, status=status, content_type=ctype,
                               charset=_charset(ctype_header), body=bytes(body), truncated=truncated,
                               redirects=redirects, elapsed_ms=int((time.monotonic() - started) * 1000))
        except FetchError:
            raise
        except ssl.SSLError:
            raise FetchError("URL_FETCH_FAILED", "A secure connection to the website could not be made "
                             "(its certificate is not valid).", 502)
        except (TimeoutError, socket.timeout):
            raise FetchError("URL_FETCH_FAILED", "The website took too long to answer.", 504)
        except (OSError, http.client.HTTPException):
            raise FetchError("URL_FETCH_FAILED", "The website could not be reached.", 502)
        finally:
            conn.close()
    raise FetchError("URL_FETCH_FAILED", "The website redirected too many times.", 502)
