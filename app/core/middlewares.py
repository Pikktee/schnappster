"""Anwendungs-Middleware: CORS (Dev) und API-Cache-Steuerung."""

import logging
import secrets
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import config
from app.core.debug_runtime import write_debug_log
from app.core.request_context import http_request_trace_id

_request_log = logging.getLogger("schnappster.http")

# Öffentliche REST-Pfade (ohne früheres globales /api-Prefix); für Cache-Control: no-store.
_API_PATH_PREFIXES: tuple[str, ...] = (
    "/ads",
    "/adsearches",
    "/aianalysislogs",
    "/errorlogs",
    "/scraperuns",
    "/settings",
    "/users",
    "/version",
)

# Next-Dev: Browser oft localhost:3000, .env manchmal nur 127.0.0.1:3000 (oder umgekehrt).
_DEV_NEXT_PAIR = ("http://localhost:3000", "http://127.0.0.1:3000")


def _is_rest_api_path(path: str) -> bool:
    if not path.startswith("/"):
        return False
    return any(path == prefix or path.startswith(prefix + "/") for prefix in _API_PATH_PREFIXES)


def _is_loopback_http_origin(origin: str) -> bool:
    return origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:")


def _ensure_dev_next_origin_aliases(origins: list[str]) -> list[str]:
    """Ergänzt das :3000-Paar bei reinen Loopback-HTTP-Origins."""
    if not origins:
        return list(_DEV_NEXT_PAIR)
    if not all(_is_loopback_http_origin(o) for o in origins):
        return origins
    out = list(dict.fromkeys(origins))  # Reihenfolge behalten, Duplikate weg
    a, b = _DEV_NEXT_PAIR
    has_a = a in out
    has_b = b in out
    if has_a ^ has_b:
        out.append(b if has_a else a)
    return out


class NoStoreApiMiddleware:
    """Setzt Cache-Control: no-store für REST-Pfade über ASGI-send (kein BaseHTTPMiddleware).

    BaseHTTPMiddleware kann bei Fehlern den Response-Pfad so umbrechen, dass aeussere
    Middleware (z. B. CORS) kein Access-Control-Allow-Origin mehr setzt — der Browser
    meldet dann CORS trotz eigentlichem 500.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        method = scope.get("method", "?")
        req_id = secrets.token_hex(4)
        request_started_at = time.time_ns() // 1_000_000
        t0 = time.perf_counter()
        response_status: int | None = None
        should_debug = path.startswith(
            ("/ads", "/adsearches", "/users/me", "/version", "/settings", "/searches")
        )

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start" and _is_rest_api_path(path):
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
                response_status = int(message.get("status", 0))
            await send(message)

        trace_cv_token = http_request_trace_id.set(req_id)
        try:
            if should_debug:
                # region agent log
                write_debug_log(
                    run_id="backend-round3",
                    hypothesis_id="H14",
                    location="app/core/middlewares.py:NoStoreApiMiddleware",
                    message="request start",
                    data={"path": path, "method": method, "req_id": req_id},
                )
                # endregion

            if path.startswith("/ads") or path.startswith("/adsearches"):
                _request_log.info("HTTP [%s] %s %s … gestartet", req_id, method, path)

            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                if _is_rest_api_path(path):
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    status_txt = str(response_status) if response_status is not None else "n/a"
                    _request_log.info(
                        "HTTP [%s] %s %s -> %s %.0fms",
                        req_id,
                        method,
                        path,
                        status_txt,
                        elapsed_ms,
                    )
            if should_debug:
                # region agent log
                write_debug_log(
                    run_id="backend-round3",
                    hypothesis_id="H14",
                    location="app/core/middlewares.py:NoStoreApiMiddleware",
                    message="request end",
                    data={
                        "path": path,
                        "status": response_status,
                        "req_id": req_id,
                        "elapsed_ms": (time.time_ns() // 1_000_000) - request_started_at,
                    },
                )
                # endregion
        finally:
            http_request_trace_id.reset(trace_cv_token)


def setup_cors(app: FastAPI) -> None:
    """
    CORS-Middleware für die Entwicklung (uv run start, Standard): Frontend auf :3000, API auf :8000;
    der Browser blockiert Cross-Origin-Requests ohne Access-Control-Allow-Origin.
    """
    allowed_origins = _ensure_dev_next_origin_aliases(
        [o.strip() for o in config.cors_allowed_origins.split(",") if o.strip()]
    )
    origin_regex = config.cors_allowed_origin_regex.strip() or None
    if origin_regex is None:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=origin_regex,
    )


def setup_no_store_api(app: FastAPI) -> None:
    """Setzt Cache-Control: no-store für REST-Pfade, damit das Frontend aktuelle Daten erhält."""
    app.add_middleware(NoStoreApiMiddleware)
