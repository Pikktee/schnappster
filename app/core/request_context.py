"""Request-weiter Kontext (von HTTP-Middleware gesetzt)."""

from __future__ import annotations

import contextvars

http_request_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "http_request_trace_id", default=""
)


def get_http_request_trace_id() -> str:
    return http_request_trace_id.get()
