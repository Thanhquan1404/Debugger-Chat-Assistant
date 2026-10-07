"""Request-ID middleware — binds a request_id to structlog contextvars (Q15)."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("X-Request-ID") or (
            f"req_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        )
        structlog.contextvars.bind_contextvars(request_id=rid)
        start = time.perf_counter()
        try:
            log.info("http.request", method=request.method, path=request.url.path)
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            log.info("http.response", duration_ms=round(duration_ms, 1))
            structlog.contextvars.unbind_contextvars("request_id")
