"""Anwendungs-Middleware: CORS (Dev) und API-Cache-Steuerung."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import config

# Next-Dev: Browser oft localhost:3000, .env manchmal nur 127.0.0.1:3000 (oder umgekehrt).
_DEV_NEXT_PAIR = ("http://localhost:3000", "http://127.0.0.1:3000")


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
    """Setzt Cache-Control: no-store für /api/* über ASGI-send (kein BaseHTTPMiddleware).

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

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start" and path.startswith("/api/"):
                headers = MutableHeaders(scope=message)
                headers["Cache-Control"] = "no-store"
            await send(message)

        await self.app(scope, receive, send_wrapper)


def setup_cors(app: FastAPI) -> None:
    """
    CORS-Middleware für die Entwicklung (uv run start --dev): Frontend auf :3000, API auf :8000;
    der Browser blockiert Cross-Origin-Requests ohne Access-Control-Allow-Origin.
    """
    allowed_origins = _ensure_dev_next_origin_aliases(
        [o.strip() for o in config.cors_allowed_origins.split(",") if o.strip()]
    )
    kwargs: dict[str, object] = {}
    if config.cors_allowed_origin_regex.strip():
        kwargs["allow_origin_regex"] = config.cors_allowed_origin_regex.strip()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        **kwargs,
    )


def setup_no_store_api(app: FastAPI) -> None:
    """Setzt Cache-Control: no-store für /api/*, damit das Frontend aktuelle Daten erhält."""
    app.add_middleware(NoStoreApiMiddleware)
