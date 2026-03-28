"""Simple in-memory rate limiter."""
import os
import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter. Per-IP, in-memory.

    Disabled when RAPTOR_RATE_LIMIT_DISABLED=true (for testing).
    """

    def __init__(self, app, general_rpm: int = 100, ai_rpm: int = 10) -> None:
        super().__init__(app)
        self.general_rpm = general_rpm
        self.ai_rpm = ai_rpm
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._disabled = os.environ.get("RAPTOR_RATE_LIMIT_DISABLED", "").lower() in ("true", "1", "yes")

    async def dispatch(self, request: Request, call_next):
        if self._disabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        now = time.time()

        # Determine limit
        is_ai = "/pipeline/start" in path or "/pipeline/advance" in path
        limit = self.ai_rpm if is_ai else self.general_rpm

        # Clean old entries (older than 60s)
        key = f"{client_ip}:{('ai' if is_ai else 'general')}"
        self._buckets[key] = [t for t in self._buckets[key] if now - t < 60]

        if len(self._buckets[key]) >= limit:
            logger.warning("[rate-limit] %s exceeded %d rpm on %s", client_ip, limit, path)
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        self._buckets[key].append(now)
        return await call_next(request)
