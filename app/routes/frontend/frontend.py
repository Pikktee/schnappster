"""Serve the statically exported Next.js frontend and SPA fallback routes."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core import get_app_root

FRONTEND_OUT_DIR = get_app_root() / "web" / "out"
INDEX_HTML = FRONTEND_OUT_DIR / "index.html"


def _serve_detail_page(section: str, id: int) -> FileResponse:
    """Serve pre-rendered detail page for section/id, or id=0 shell if missing."""
    candidate = FRONTEND_OUT_DIR / section / str(id) / "index.html"
    if candidate.is_file():
        return FileResponse(candidate)
    fallback = FRONTEND_OUT_DIR / section / "0" / "index.html"
    return FileResponse(fallback if fallback.is_file() else INDEX_HTML)


router = APIRouter(include_in_schema=False)


# SPA fallback: direct hits to /searches/5, /ads/21 get the id=0 HTML shell
# so the client router can hydrate and fetch data for the actual ID.
@router.api_route("/searches/{id:int}", methods=["GET", "HEAD"])
def serve_search_detail(id: int):
    """Serve search detail SPA shell for the given id."""
    return _serve_detail_page("searches", id)


@router.api_route("/ads/{id:int}", methods=["GET", "HEAD"])
def serve_ad_detail(id: int):
    """Serve ad detail SPA shell for the given id."""
    return _serve_detail_page("ads", id)


def mount_frontend(app):
    """Mount the static Next.js export at / (call after including router)."""
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_OUT_DIR), html=True, check_dir=False),
        name="web",
    )
