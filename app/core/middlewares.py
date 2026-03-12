"""Application middlewares: CORS (dev) and API cache-control."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class NoStoreApiMiddleware(BaseHTTPMiddleware):
    """Set Cache-Control: no-store on /api/* so the frontend always gets fresh data."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


def setup_cors(app: FastAPI) -> None:
    """
    Add CORS middleware for development (uv run start --dev): frontend on :3000, API on :8000;
    the browser blocks cross-origin requests unless Access-Control-Allow-Origin is set.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_no_store_api(app: FastAPI) -> None:
    """Set Cache-Control: no-store on /api/* so the frontend gets fresh data."""
    app.add_middleware(NoStoreApiMiddleware)
