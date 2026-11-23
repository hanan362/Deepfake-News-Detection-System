"""Small in-memory sliding-window rate limiter (per client address).

It protects a single server process. Behind several workers or servers, use a shared store (e.g. Redis).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings

AUTH_PATHS = ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password")


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def reset(self) -> None:
        self._hits.clear()

    def check(self, client: str, bucket: str, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        q = self._hits[(client, bucket)]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and request.method != "OPTIONS":
            s = get_settings()
            client = request.client.host if request.client else "unknown"
            is_auth = path in AUTH_PATHS
            bucket, limit = ("auth", s.auth_rate_limit_per_minute) if is_auth else ("general", s.rate_limit_per_minute)
            if not limiter.check(client, bucket, limit):
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": "60"},
                    content={"error": {"code": "RATE_LIMITED", "message": "Too many requests. Please wait a minute and try again.", "details": None}},
                )
        return await call_next(request)
