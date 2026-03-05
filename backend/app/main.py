from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
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
INDEX_HTML = FRONTEND_OUT_DIR / "index.html"


# SPA fallback: dynamic routes like /searches/1, /ads/2 are only pre-rendered for id=0.
# All other IDs must get index.html so the client-side router can load the page.
@app.get("/searches/{path:path}")
def serve_searches_spa(path: str):
    return FileResponse(INDEX_HTML)


@app.get("/ads/{path:path}")
def serve_ads_spa(path: str):
    return FileResponse(INDEX_HTML)


app.mount(
    "/",
    StaticFiles(directory=FRONTEND_OUT_DIR, html=True, check_dir=False),
    name="frontend",
)
