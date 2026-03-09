from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core import BackgroundJobs, get_app_root, init_db, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()

    jobs = BackgroundJobs()
    jobs.start()

    yield

    jobs.stop()


app = FastAPI(
    title="Schnappster",
    version="0.1.0",
    description="Kleinanzeigen.de Schnäppchen-Finder",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# Serve the statically exported Next.js frontend from web/out
FRONTEND_OUT_DIR = get_app_root() / "web" / "out"
INDEX_HTML = FRONTEND_OUT_DIR / "index.html"


def _serve_detail_page(section: str, id: int) -> FileResponse:
    """Serve the pre-rendered detail page for *id*, falling back to the id=0 shell."""
    candidate = FRONTEND_OUT_DIR / section / str(id) / "index.html"
    if candidate.is_file():
        return FileResponse(candidate)
    fallback = FRONTEND_OUT_DIR / section / "0" / "index.html"
    return FileResponse(fallback if fallback.is_file() else INDEX_HTML)


# SPA fallback for dynamic detail pages only (/searches/5, /ads/21, …).
# Next.js only pre-renders id=0; other IDs get the id=0 HTML shell so the
# client-side router can hydrate and fetch data for the actual ID.
@app.api_route("/searches/{id:int}", methods=["GET", "HEAD"], include_in_schema=False)
def serve_search_detail(id: int):
    return _serve_detail_page("searches", id)


@app.api_route("/ads/{id:int}", methods=["GET", "HEAD"], include_in_schema=False)
def serve_ad_detail(id: int):
    return _serve_detail_page("ads", id)


app.mount(
    "/",
    StaticFiles(directory=FRONTEND_OUT_DIR, html=True, check_dir=False),
    name="web",
)
