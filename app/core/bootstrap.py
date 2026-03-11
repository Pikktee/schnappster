"""
Builds the FastAPI application with middleware, routes, and static frontend.
"""

from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import init_db, setup_logging
from app.core.background_jobs import get_background_jobs
from app.routes import api_router, frontend_router, mount_frontend


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()

    jobs = get_background_jobs()
    jobs.start()

    yield

    jobs.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Schnappster",
        version=version("schnappster"),
        description="Kleinanzeigen.de Schnäppchen-Finder",
        lifespan=lifespan,
    )

    # CORS: This middleware sets the required headers for development mode
    #
    # In development mode (uv run start --dev), the frontend runs on :3000
    # and the API on :8000 (different origins).
    # The browser blocks API requests from :3000 to :8000 unless the server sends the
    # Access-Control-Allow-Origin header.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include the API and frontend routers
    app.include_router(api_router)
    app.include_router(frontend_router)

    # Mount the frontend static files
    mount_frontend(app)

    return app
