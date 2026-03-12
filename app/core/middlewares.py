"""Anwendungs-Middleware: CORS (Dev) und API-Cache-Steuerung."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class NoStoreApiMiddleware(BaseHTTPMiddleware):
    """Setzt Cache-Control: no-store für /api/*, damit das Frontend immer aktuelle Daten erhält."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


def setup_cors(app: FastAPI) -> None:
    """
    CORS-Middleware für die Entwicklung (uv run start --dev): Frontend auf :3000, API auf :8000;
    der Browser blockiert Cross-Origin-Requests ohne Access-Control-Allow-Origin.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_no_store_api(app: FastAPI) -> None:
    """Setzt Cache-Control: no-store für /api/*, damit das Frontend aktuelle Daten erhält."""
    app.add_middleware(NoStoreApiMiddleware)
