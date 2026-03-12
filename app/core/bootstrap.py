"""FastAPI-App mit Middleware, Routen und statischem Frontend aufbauen."""

from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from app.core import init_db, setup_logging
from app.core.background_jobs import get_background_jobs
from app.core.middlewares import setup_cors, setup_no_store_api
from app.routes import api_router, frontend_router, mount_frontend


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start: Logging einrichten, DB initialisieren, Hintergrund-Jobs starten; Ende: Jobs stoppen."""
    setup_logging()
    init_db()

    jobs = get_background_jobs()
    jobs.start()

    yield

    jobs.stop()


def create_app() -> FastAPI:
    """Erstellt und konfiguriert die FastAPI-Anwendung."""
    app = FastAPI(
        title="Schnappster",
        version=version("schnappster"),
        description="Kleinanzeigen.de Schnäppchen-Finder",
        lifespan=lifespan,
    )

    setup_cors(app)
    setup_no_store_api(app)

    # API- und Frontend-Router einbinden
    app.include_router(api_router)
    app.include_router(frontend_router)

    # Statische Frontend-Dateien bereitstellen
    mount_frontend(app)

    return app
