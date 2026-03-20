"""
middleware.py
-------------
Production middleware:
  - RateLimitMiddleware  : in-memory sliding window rate limiter
  - RequestLoggingMiddleware : structured request/response logging

Rate limiting strategy:
  - Per-IP sliding window (60s)
  - Auth endpoints: 10 req/min  (prevent brute force)
  - Screen endpoint: 5 req/min  (expensive — LLM + embeddings)
  - All other:      60 req/min  (generous for normal usage)
  - Returns 429 with Retry-After header
"""

import time
import logging
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ── Rate limit config per route prefix ───────────────────────────────────────
RATE_LIMITS = {
    "/auth/login":      (10, 60),   # 10 requests per 60s
    "/auth/signup":     (10, 60),
    "/auth/resend-otp": (5,  60),
    "/auth/verify-otp": (10, 60),
    "/screen":          (5,  60),   # expensive endpoint
}
DEFAULT_RATE = (60, 60)             # 60 requests per 60s


def _get_limit(path: str) -> tuple[int, int]:
    for prefix, limit in RATE_LIMITS.items():
        if path.startswith(prefix):
            return limit
    return DEFAULT_RATE


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter.
    State is in-memory — resets on restart.
    For multi-process deployments, swap _windows for Redis.
    """

    def __init__(self, app):
        super().__init__(app)
        # {(ip, path_prefix): deque of timestamps}
        self._windows: dict = defaultdict(deque)

    def _get_ip(self, request: Request) -> str:
        # Respect X-Forwarded-For from reverse proxy (nginx, Cloudflare, etc.)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        ip    = self._get_ip(request)
        path  = request.url.path
        limit, window = _get_limit(path)
        key   = (ip, path)
        now   = time.time()
        dq    = self._windows[key]

        # Evict timestamps outside the window
        while dq and dq[0] < now - window:
            dq.popleft()

        if len(dq) >= limit:
            retry_after = int(window - (now - dq[0])) + 1
            logger.warning("Rate limit hit: ip=%s path=%s", ip, path)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Too many requests. Please wait {retry_after}s before retrying."
                },
                headers={"Retry-After": str(retry_after)},
            )

        dq.append(now)
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "%s %s → %d  (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        # Add timing header for debugging
        response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
        return response