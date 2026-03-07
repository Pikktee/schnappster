from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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
# List pages (/searches, /ads, /logs, /settings) are fully pre-rendered
# and served directly by StaticFiles below.
# Support both GET and HEAD so router prefetch and RSC requests don't 404.
@app.api_route("/searches/{id:int}", methods=["GET", "HEAD"])
def serve_search_detail(id: int):
    return _serve_detail_page("searches", id)


@app.api_route("/searches/{id:int}/", methods=["GET", "HEAD"])
def serve_search_detail_slash(id: int):
    return _serve_detail_page("searches", id)


@app.api_route("/ads/{id:int}", methods=["GET", "HEAD"])
def serve_ad_detail(id: int):
    return _serve_detail_page("ads", id)


@app.api_route("/ads/{id:int}/", methods=["GET", "HEAD"])
def serve_ad_detail_slash(id: int):
    return _serve_detail_page("ads", id)


def _serve_rsc_or_fallback(section: str, id: int) -> FileResponse | None:
    """Serve RSC payload (index.txt) if present, else None (caller may return 204)."""
    for sid in (id, 0):
        candidate = FRONTEND_OUT_DIR / section / str(sid) / "index.txt"
        if candidate.is_file():
            return FileResponse(candidate, media_type="text/plain; charset=utf-8")
    return None


@app.api_route("/searches/{id:int}/index.txt", methods=["GET", "HEAD"])
def serve_search_rsc(id: int):
    r = _serve_rsc_or_fallback("searches", id)
    if r is not None:
        return r
    return Response(status_code=204)


@app.api_route("/ads/{id:int}/index.txt", methods=["GET", "HEAD"])
def serve_ad_rsc(id: int):
    r = _serve_rsc_or_fallback("ads", id)
    if r is not None:
        return r
    return Response(status_code=204)


app.mount(
    "/",
    StaticFiles(directory=FRONTEND_OUT_DIR, html=True, check_dir=False),
    name="web",
)
