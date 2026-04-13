"""FastAPI-App mit Middleware und API-Routen aufbauen."""

import logging
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core import init_db, setup_logging
from app.core.auth import close_auth_http_client
from app.core.background_jobs import get_background_jobs
from app.core.fastapi_app import SchnappsterFastAPI
from app.core.middlewares import setup_cors, setup_no_store_api
from app.routes import api_router


@asynccontextmanager
async def lifespan(app: SchnappsterFastAPI):
    """Start: Logging einrichten, DB initialisieren, Hintergrund-Jobs starten;
    Ende: Jobs stoppen.
    """
    setup_logging()
    init_db()

    jobs = get_background_jobs()
    jobs.start()

    yield

    jobs.stop()
    await close_auth_http_client()


def create_app() -> SchnappsterFastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung."""
    app = SchnappsterFastAPI(
        title="Schnappster",
        version=version("schnappster"),
        description="Kleinanzeigen.de Schnäppchen-Finder",
        lifespan=lifespan,
    )

    # NoStore zuerst registriert, dann CORS (insert(0) → user_middleware = [CORS, NoStore]).
    # SchnappsterFastAPI legt diese Schichten ausserhalb von ServerErrorMiddleware, damit
    # 500-Antworten weiterhin Access-Control-Allow-Origin erhalten.
    setup_no_store_api(app)
    setup_cors(app)

    # API-Router einbinden
    app.include_router(api_router)

    @app.exception_handler(500)
    async def server_error_json(_request: Request, exc: Exception) -> JSONResponse:
        """JSON-500 fuer apiFetch; ausgeloest von ServerErrorMiddleware."""
        logging.getLogger(__name__).error(
            "Serverfehler (500): %s",
            exc,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Interner Serverfehler — bitte Server-Logs prüfen."},
        )

    return app
