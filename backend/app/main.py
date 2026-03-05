from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core import get_app_root, init_db, setup_logging, start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Schnappster",
    version="0.1.0",
    description="Kleinanzeigen.de Schnäppchen-Finder",
    lifespan=lifespan,
)

app.include_router(api_router)


# Serve the statically exported Next.js frontend from frontend/out
FRONTEND_OUT_DIR = get_app_root().parent / "frontend" / "out"

app.mount(
    "/",
    StaticFiles(directory=FRONTEND_OUT_DIR, html=True, check_dir=False),
    name="frontend",
)
