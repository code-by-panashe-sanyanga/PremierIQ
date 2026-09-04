from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_SECRET_NAMES = (
    "FOOTBALL_DATA_API_KEY",
    "OPENWEATHER_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)

_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|token|authorization|x-auth-token)\s*[:=]\s*['\"]?[^\s'\"]+",
    re.IGNORECASE,
)


def debug_enabled() -> bool:
    return os.getenv("PREMIERIQ_DEBUG", "").strip().lower() in {"1", "true", "yes"}


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = [part.strip() for part in raw.split(",") if part.strip() and part.strip() != "*"]
    return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]


def trusted_hosts() -> list[str]:
    raw = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1")
    hosts = [part.strip() for part in raw.split(",") if part.strip()]
    return hosts or ["localhost", "127.0.0.1"]


def redact(value: str) -> str:
    text = value
    for name in _SECRET_NAMES:
        secret = os.getenv(name, "")
        if secret:
            text = text.replace(secret, "[redacted]")
    return _KEY_PATTERN.sub("[redacted]", text)


def public_error_detail() -> str:
    return "Upstream data is unavailable."


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:128]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_hits: int = 90, window_s: int = 60):
        super().__init__(app)
        self.max_hits = max_hits
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        now = time.monotonic()
        bucket = self._hits[client_ip(request)]
        cutoff = now - self.window_s
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_hits:
            return JSONResponse({"detail": "Too many requests."}, status_code=429)
        bucket.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cache-Control", "no-store")
        return response
